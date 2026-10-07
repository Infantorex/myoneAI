"""Monitoring module for myoneAI / Tamil JARVIS (Phase 9).

Provides lightweight, event-driven hardware and OS health telemetry:
- CPU, RAM, Disk, Battery, Network, and Process metrics.
- Configurable thresholds (WARNING, CRITICAL).
- Cooldown-managed alerts preventing notification spam.
- Slow system bottleneck diagnosis.
- Seamless integration with Phase 8 tool execution system.
"""

from app.monitoring.alerts import AlertManager, alert_manager
from app.monitoring.battery import get_battery_metrics
from app.monitoring.cpu import get_cpu_metrics
from app.monitoring.disk import get_disk_metrics
from app.monitoring.manager import MonitoringManager, monitoring_manager
from app.monitoring.memory import get_memory_metrics
from app.monitoring.models import (
    AlertLevel,
    BatteryMetrics,
    CPUMetrics,
    DiskMetrics,
    MemoryMetrics,
    MonitoringSnapshot,
    NetworkMetrics,
    ProcessItem,
    ProcessMetrics,
    SystemAlert,
)
from app.monitoring.network import get_network_metrics
from app.monitoring.processes import get_process_metrics, get_top_processes
from app.monitoring.system import get_system_summary
from app.monitoring.thresholds import ThresholdEngine, threshold_engine

# Legacy backward-compatible aliases
get_battery_status = get_battery_metrics
get_network_status = get_network_metrics

__all__ = [
    # Models
    "AlertLevel",
    "CPUMetrics",
    "MemoryMetrics",
    "DiskMetrics",
    "BatteryMetrics",
    "NetworkMetrics",
    "ProcessItem",
    "ProcessMetrics",
    "MonitoringSnapshot",
    "SystemAlert",
    # Subsystem Collectors
    "get_cpu_metrics",
    "get_memory_metrics",
    "get_disk_metrics",
    "get_battery_metrics",
    "get_network_metrics",
    "get_process_metrics",
    "get_top_processes",
    "get_system_summary",
    "get_battery_status",
    "get_network_status",
    # Engine & Managers
    "ThresholdEngine",
    "threshold_engine",
    "AlertManager",
    "alert_manager",
    "MonitoringManager",
    "monitoring_manager",
]
