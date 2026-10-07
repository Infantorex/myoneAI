"""Monitoring manager orchestrating system metrics, thresholds, and alerts (Phase 9).

Provides on-demand snapshots, background periodic health checks, and slow PC diagnostics.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.core.config import Settings, get_settings
from app.core.events import EventBus, event_bus
from app.monitoring.alerts import AlertManager, alert_manager
from app.monitoring.battery import get_battery_metrics
from app.monitoring.cpu import get_cpu_metrics
from app.monitoring.disk import get_disk_metrics
from app.monitoring.memory import get_memory_metrics
from app.monitoring.models import MonitoringSnapshot, SystemAlert
from app.monitoring.network import get_network_metrics
from app.monitoring.processes import get_process_metrics, get_top_processes
from app.monitoring.thresholds import ThresholdEngine, threshold_engine

logger = logging.getLogger("myoneAI.monitoring.manager")


class MonitoringManager:
    """Central orchestrator for lightweight system monitoring and health alerts."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        threshold_engine_instance: Optional[ThresholdEngine] = None,
        alert_manager_instance: Optional[AlertManager] = None,
        event_bus_instance: Optional[EventBus] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.threshold_engine = threshold_engine_instance or threshold_engine
        self.alert_manager = alert_manager_instance or alert_manager
        self.event_bus = event_bus_instance or event_bus
        self._task: Optional[asyncio.Task] = None
        self._is_running: bool = False

    @property
    def is_running(self) -> bool:
        """True if the background monitoring loop is active."""
        return self._is_running

    def get_snapshot_sync(
        self,
        include_processes: bool = False,
        process_limit: int = 5,
        sample_interval: Optional[float] = 0.1,
    ) -> MonitoringSnapshot:
        """Synchronously collect snapshot across all system telemetry sources.

        Args:
            include_processes: If True, include top process information.
            process_limit: Maximum processes per category if included.
            sample_interval: CPU sampling interval (default 0.1s).

        Returns:
            MonitoringSnapshot instance.
        """
        cpu = get_cpu_metrics(sample_interval=sample_interval)
        mem = get_memory_metrics()
        disk = get_disk_metrics()
        battery = get_battery_metrics()
        network = get_network_metrics(check_latency=False)
        procs = get_process_metrics(limit=process_limit) if include_processes else None

        return MonitoringSnapshot(
            cpu=cpu,
            memory=mem,
            disk=disk,
            battery=battery,
            network=network,
            processes=procs,
        )

    async def get_snapshot(
        self,
        include_processes: bool = False,
        process_limit: int = 5,
        sample_interval: Optional[float] = 0.1,
    ) -> MonitoringSnapshot:
        """Asynchronously collect live telemetry snapshot without blocking event loop.

        Args:
            include_processes: If True, include top process information.
            process_limit: Maximum processes per category.
            sample_interval: CPU sampling interval.

        Returns:
            MonitoringSnapshot instance.
        """
        return await asyncio.to_thread(
            self.get_snapshot_sync,
            include_processes=include_processes,
            process_limit=process_limit,
            sample_interval=sample_interval,
        )

    async def check_and_alert(self) -> List[SystemAlert]:
        """Perform a single health check and dispatch any triggered alerts.

        Returns:
            List of dispatched SystemAlert instances.
        """
        snapshot = await self.get_snapshot(include_processes=False)
        raw_alerts = self.threshold_engine.evaluate(snapshot)
        dispatched = self.alert_manager.process_alerts(raw_alerts)

        if dispatched and self.event_bus:
            for alert in dispatched:
                self.event_bus.emit("monitoring.alert", alert.to_dict())

        return dispatched

    async def _background_loop(self) -> None:
        """Periodic background evaluation loop with adaptive battery power awareness."""
        base_interval = max(5, int(getattr(self.settings, "monitoring_interval_seconds", 60)))
        logger.info("System monitoring background task started (base_interval=%ds)", base_interval)

        while self._is_running:
            try:
                await self.check_and_alert()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error in monitoring background loop: %s", exc, exc_info=True)

            # Battery-Aware Optimization: throttles monitoring duty-cycle on battery power
            current_interval = base_interval
            try:
                bat = get_battery_metrics()
                if bat.is_available and not bat.power_plugged:
                    # Double interval on battery to conserve CPU duty cycle and power
                    current_interval = min(120, base_interval * 2)
            except Exception:
                current_interval = base_interval

            try:
                await asyncio.sleep(current_interval)
            except asyncio.CancelledError:
                break

        logger.info("System monitoring background task stopped")

    def start_background_monitoring(self) -> bool:
        """Start the periodic background health checker if enabled in configuration."""
        if not getattr(self.settings, "monitoring_enabled", True):
            logger.info("Monitoring is disabled by configuration (MONITORING_ENABLED=false)")
            return False

        if self._is_running:
            logger.debug("Monitoring background loop is already running")
            return True

        self._is_running = True
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._background_loop())
            return True
        except RuntimeError:
            logger.warning("No active asyncio loop available to start background monitoring")
            self._is_running = False
            return False

    def stop_background_monitoring(self) -> None:
        """Gracefully stop the background monitoring loop."""
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None

    async def diagnose_slow_system(self, process_limit: int = 5) -> Dict[str, Any]:
        """Analyze current system health and provide bottleneck diagnosis with recommendations.

        Returns:
            Dictionary containing observed_metrics, diagnosis_summary,
            tamil_summary, and actionable recommendations.
        """
        snapshot = await self.get_snapshot(include_processes=True, process_limit=process_limit)

        issues: List[str] = []
        tamil_issues: List[str] = []
        recommendations: List[str] = []
        tamil_recommendations: List[str] = []

        # 1. RAM Analysis
        if snapshot.memory:
            if snapshot.memory.percent >= self.settings.memory_warning_threshold:
                issues.append(f"RAM usage is high at {snapshot.memory.percent:.0f}%")
                tamil_issues.append(f"RAM பயன்பாடு {snapshot.memory.percent:.0f}% ஆக அதிகம் உள்ளது")
                if snapshot.processes and snapshot.processes.top_memory:
                    top_app = snapshot.processes.top_memory[0]
                    recommendations.append(f"'{top_app.name}' is using {top_app.memory_mb:.0f}MB RAM. Closing unused tabs/apps will free memory.")
                    tamil_recommendations.append(f"'{top_app.name}' செயலி {top_app.memory_mb:.0f}MB நினைவகத்தை பயன்படுத்துகிறது. அதை மூடுவது வேகத்தை அதிகரிக்கும்.")
                else:
                    recommendations.append("Closing unused applications may improve performance.")
                    tamil_recommendations.append("பயன்படுத்தாத செயலிகளை மூடுவது செயல்திறனை அதிகரிக்கும்.")

        # 2. CPU Analysis
        if snapshot.cpu:
            if snapshot.cpu.usage_percent >= self.settings.cpu_warning_threshold:
                issues.append(f"CPU utilization is heavy at {snapshot.cpu.usage_percent:.1f}%")
                tamil_issues.append(f"CPU பயன்பாடு {snapshot.cpu.usage_percent:.1f}% ஆக அதிக சுமையில் உள்ளது")
                if snapshot.processes and snapshot.processes.top_cpu:
                    top_cpu_app = snapshot.processes.top_cpu[0]
                    recommendations.append(f"'{top_cpu_app.name}' is consuming {top_cpu_app.cpu_percent:.1f}% CPU.")
                    tamil_recommendations.append(f"'{top_cpu_app.name}' செயலி {top_cpu_app.cpu_percent:.1f}% CPU பயன்படுத்துகிறது.")

        # 3. Disk Analysis
        if snapshot.disk:
            if snapshot.disk.percent >= self.settings.disk_warning_threshold:
                issues.append(f"Disk storage is nearly full ({snapshot.disk.free_gb:.1f}GB free)")
                tamil_issues.append(f"வட்டு இடம் குறைவாக உள்ளது ({snapshot.disk.free_gb:.1f}GB மட்டுமே உள்ளது)")
                recommendations.append("Cleaning temporary files or moving large files to external storage will help.")
                tamil_recommendations.append("தற்காலிக கோப்புகளை நீக்குவது வட்டு இடத்தை விடுவிக்கும்.")

        # 4. Battery / Power Throttling
        if snapshot.battery and snapshot.battery.is_available:
            if not snapshot.battery.power_plugged and snapshot.battery.percent <= self.settings.battery_low_threshold:
                issues.append(f"Laptop is on battery ({snapshot.battery.percent:.0f}%) and may be power-throttled")
                tamil_issues.append(f"லேப்டாப் பேட்டரியில் இயங்குகிறது ({snapshot.battery.percent:.0f}%)")
                recommendations.append("Connecting the AC charger may restore maximum CPU clock speeds.")
                tamil_recommendations.append("சார்ஜரை இணைத்தால் முழு வேகத்தில் இயங்கும்.")

        # If everything is within normal limits
        if not issues:
            summary = "System resources are normal. CPU, RAM, and Disk are within healthy operating parameters."
            tamil_summary = "உங்கள் லேப்டாப் சீராக இயங்குகிறது. CPU, RAM மற்றும் சேமிப்பகம் அனைத்தும் சரியான அளவில் உள்ளன."
            recommendations.append("No critical bottlenecks detected. If sluggishness persists, check background browser extensions or restart.")
            tamil_recommendations.append("முக்கிய சிக்கல்கள் ஏதுமில்லை. தேவைப்பட்டால் உலாவியை மறுதொடக்கம் செய்யலாம்.")
        else:
            summary = "; ".join(issues) + "."
            tamil_summary = "; ".join(tamil_issues) + "."

        result = {
            "status": "warning" if issues else "normal",
            "observed_metrics": snapshot.to_dict(),
            "diagnosis_summary": summary,
            "tamil_summary": tamil_summary,
            "recommendations": recommendations,
            "tamil_recommendations": tamil_recommendations,
        }

        if self.event_bus:
            self.event_bus.emit("monitoring.diagnosis", result)

        return result


# Global MonitoringManager singleton
monitoring_manager = MonitoringManager()
