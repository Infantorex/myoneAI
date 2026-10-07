"""Data models and schemas for lightweight system monitoring & alerts (Phase 9)."""

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AlertLevel(str, Enum):
    """Severity tier for health alerts."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class CPUMetrics:
    """Instantaneous CPU utilization and core topology."""
    usage_percent: float
    logical_cores: int
    physical_cores: Optional[int] = None
    frequency_mhz: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryMetrics:
    """System RAM utilization breakdown."""
    total_mb: float
    used_mb: float
    available_mb: float
    percent: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DiskMetrics:
    """Storage utilization for the active drive."""
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float
    mount_point: str = "C:\\"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BatteryMetrics:
    """Laptop battery power status and charge levels."""
    percent: float
    power_plugged: bool
    secsleft: Optional[int] = None
    is_charging: bool = False
    is_available: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NetworkMetrics:
    """Basic network connectivity and latency telemetry."""
    is_connected: bool
    hostname: str
    ip_address: Optional[str] = None
    latency_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProcessItem:
    """Resource metrics for an individual process."""
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_mb: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProcessMetrics:
    """Top resource-consuming processes overview."""
    top_memory: List[ProcessItem] = field(default_factory=list)
    top_cpu: List[ProcessItem] = field(default_factory=list)
    total_processes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "top_memory": [p.to_dict() for p in self.top_memory],
            "top_cpu": [p.to_dict() for p in self.top_cpu],
            "total_processes": self.total_processes,
        }


@dataclass
class MonitoringSnapshot:
    """Normalized point-in-time health telemetry across all subsystems."""
    timestamp: float = field(default_factory=time.time)
    cpu: Optional[CPUMetrics] = None
    memory: Optional[MemoryMetrics] = None
    disk: Optional[DiskMetrics] = None
    battery: Optional[BatteryMetrics] = None
    network: Optional[NetworkMetrics] = None
    processes: Optional[ProcessMetrics] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to JSON-serializable dictionary."""
        return {
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu.usage_percent if self.cpu else None,
            "memory_percent": self.memory.percent if self.memory else None,
            "disk_percent": self.disk.percent if self.disk else None,
            "battery_percent": self.battery.percent if (self.battery and self.battery.is_available) else None,
            "battery_plugged": self.battery.power_plugged if (self.battery and self.battery.is_available) else None,
            "network_available": self.network.is_connected if self.network else None,
            "cpu": self.cpu.to_dict() if self.cpu else None,
            "memory": self.memory.to_dict() if self.memory else None,
            "disk": self.disk.to_dict() if self.disk else None,
            "battery": self.battery.to_dict() if self.battery else None,
            "network": self.network.to_dict() if self.network else None,
            "processes": self.processes.to_dict() if self.processes else None,
        }

    def to_summary(self) -> str:
        """Concise summary for AI conversational context."""
        parts = []
        if self.cpu:
            parts.append(f"CPU: {self.cpu.usage_percent:.1f}%")
        if self.memory:
            parts.append(f"RAM: {self.memory.percent:.0f}% ({self.memory.used_mb / 1024:.1f}GB / {self.memory.total_mb / 1024:.1f}GB)")
        if self.disk:
            parts.append(f"Disk: {self.disk.percent:.0f}% (Free: {self.disk.free_gb:.1f}GB)")
        if self.battery and self.battery.is_available:
            charge_state = "charging" if self.battery.power_plugged else "on battery"
            parts.append(f"Battery: {self.battery.percent:.0f}% ({charge_state})")
        if self.network:
            status = "connected" if self.network.is_connected else "disconnected"
            parts.append(f"Network: {status}")
        return " | ".join(parts)


@dataclass
class SystemAlert:
    """Represents a threshold-triggered health alert."""
    level: AlertLevel
    category: str
    metric_name: str
    current_value: float
    threshold: float
    message: str
    tamil_message: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "category": self.category,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "message": self.message,
            "tamil_message": self.tamil_message,
            "timestamp": self.timestamp,
        }
