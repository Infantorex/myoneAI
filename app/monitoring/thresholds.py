"""Threshold evaluation engine for system telemetry alerts (Phase 9).

Compares live metric snapshots against configurable warning and critical boundaries.
"""

import logging
from typing import List, Optional

from app.core.config import Settings, get_settings
from app.monitoring.models import AlertLevel, MonitoringSnapshot, SystemAlert

logger = logging.getLogger("myoneAI.monitoring.thresholds")


class ThresholdEngine:
    """Evaluates telemetry snapshots against configured health thresholds."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def evaluate(self, snapshot: MonitoringSnapshot) -> List[SystemAlert]:
        """Check all subsystems in snapshot and return triggered alerts.

        Args:
            snapshot: MonitoringSnapshot with current metrics.

        Returns:
            List of SystemAlert instances.
        """
        alerts: List[SystemAlert] = []

        # 1. CPU Evaluation
        if snapshot.cpu:
            cpu_val = snapshot.cpu.usage_percent
            if cpu_val >= self.settings.cpu_critical_threshold:
                alerts.append(SystemAlert(
                    level=AlertLevel.CRITICAL,
                    category="cpu",
                    metric_name="CPU Utilization",
                    current_value=cpu_val,
                    threshold=self.settings.cpu_critical_threshold,
                    message=f"CRITICAL: CPU usage is extremely high at {cpu_val:.1f}%.",
                    tamil_message=f"எச்சரிக்கை: CPU பயன்பாடு மிக அதிகமாக {cpu_val:.1f}% உள்ளது.",
                ))
            elif cpu_val >= self.settings.cpu_warning_threshold:
                alerts.append(SystemAlert(
                    level=AlertLevel.WARNING,
                    category="cpu",
                    metric_name="CPU Utilization",
                    current_value=cpu_val,
                    threshold=self.settings.cpu_warning_threshold,
                    message=f"WARNING: CPU usage is high at {cpu_val:.1f}%.",
                    tamil_message=f"கவனிக்க: CPU பயன்பாடு {cpu_val:.1f}% ஆக உயர்ந்துள்ளது.",
                ))

        # 2. Memory / RAM Evaluation
        if snapshot.memory:
            mem_val = snapshot.memory.percent
            if mem_val >= self.settings.memory_critical_threshold:
                alerts.append(SystemAlert(
                    level=AlertLevel.CRITICAL,
                    category="memory",
                    metric_name="RAM Usage",
                    current_value=mem_val,
                    threshold=self.settings.memory_critical_threshold,
                    message=f"CRITICAL: RAM usage is critical at {mem_val:.1f}%.",
                    tamil_message=f"எச்சரிக்கை: RAM பயன்பாடு மிக அதிகமாக {mem_val:.1f}% உள்ளது.",
                ))
            elif mem_val >= self.settings.memory_warning_threshold:
                alerts.append(SystemAlert(
                    level=AlertLevel.WARNING,
                    category="memory",
                    metric_name="RAM Usage",
                    current_value=mem_val,
                    threshold=self.settings.memory_warning_threshold,
                    message=f"WARNING: RAM usage is high at {mem_val:.1f}%.",
                    tamil_message=f"கவனிக்க: RAM பயன்பாடு {mem_val:.1f}% ஆக உயர்ந்துள்ளது.",
                ))

        # 3. Disk Storage Evaluation
        if snapshot.disk:
            disk_val = snapshot.disk.percent
            if disk_val >= self.settings.disk_critical_threshold:
                alerts.append(SystemAlert(
                    level=AlertLevel.CRITICAL,
                    category="disk",
                    metric_name="Disk Usage",
                    current_value=disk_val,
                    threshold=self.settings.disk_critical_threshold,
                    message=f"CRITICAL: Disk storage is nearly full ({disk_val:.1f}% used, Free: {snapshot.disk.free_gb:.1f}GB).",
                    tamil_message=f"எச்சரிக்கை: வட்டு நினைவகம் நிறைவடைய உள்ளது ({disk_val:.1f}% பயன்பாடு).",
                ))
            elif disk_val >= self.settings.disk_warning_threshold:
                alerts.append(SystemAlert(
                    level=AlertLevel.WARNING,
                    category="disk",
                    metric_name="Disk Usage",
                    current_value=disk_val,
                    threshold=self.settings.disk_warning_threshold,
                    message=f"WARNING: Disk space is low ({disk_val:.1f}% used, Free: {snapshot.disk.free_gb:.1f}GB).",
                    tamil_message=f"கவனிக்க: வட்டு இடம் குறைவாக உள்ளது ({snapshot.disk.free_gb:.1f}GB மட்டுமே உள்ளது).",
                ))

        # 4. Battery Evaluation (Only when discharging / on battery)
        if snapshot.battery and snapshot.battery.is_available and not snapshot.battery.power_plugged:
            batt_val = snapshot.battery.percent
            if batt_val <= self.settings.battery_critical_threshold:
                alerts.append(SystemAlert(
                    level=AlertLevel.CRITICAL,
                    category="battery",
                    metric_name="Battery Level",
                    current_value=batt_val,
                    threshold=self.settings.battery_critical_threshold,
                    message=f"CRITICAL: Battery is critically low ({batt_val:.0f}%). Please connect the charger immediately.",
                    tamil_message=f"எச்சரிக்கை: பேட்டரி மிக குறைவாக ({batt_val:.0f}%) உள்ளது. சார்ஜரை இணைக்கவும்.",
                ))
            elif batt_val <= self.settings.battery_low_threshold:
                alerts.append(SystemAlert(
                    level=AlertLevel.WARNING,
                    category="battery",
                    metric_name="Battery Level",
                    current_value=batt_val,
                    threshold=self.settings.battery_low_threshold,
                    message=f"WARNING: Battery is low ({batt_val:.0f}%).",
                    tamil_message=f"கவனிக்க: பேட்டரி குறைவாக ({batt_val:.0f}%) உள்ளது.",
                ))

        return alerts


# Global threshold engine singleton
threshold_engine = ThresholdEngine()
