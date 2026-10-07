"""Unit tests for Phase 9 System Monitoring, Thresholds, and Alerts."""

import pytest

from app.monitoring.alerts import AlertManager
from app.monitoring.battery import get_battery_metrics
from app.monitoring.cpu import get_cpu_metrics
from app.monitoring.disk import get_disk_metrics
from app.monitoring.manager import MonitoringManager
from app.monitoring.memory import get_memory_metrics
from app.monitoring.models import CPUMetrics, MemoryMetrics, MonitoringSnapshot
from app.monitoring.network import get_network_metrics
from app.monitoring.processes import get_process_metrics
from app.monitoring.thresholds import ThresholdEngine


def test_individual_metrics_collection():
    """Verify each hardware telemetry collector returns valid structured models."""
    cpu = get_cpu_metrics(sample_interval=None)
    assert isinstance(cpu.usage_percent, (int, float))

    mem = get_memory_metrics()
    assert isinstance(mem.percent, (int, float))
    assert mem.total_mb > 0

    disk = get_disk_metrics()
    assert isinstance(disk.percent, (int, float))

    bat = get_battery_metrics()
    assert bat.is_available in (True, False)

    net = get_network_metrics(check_latency=False)
    assert net.is_connected in (True, False)


def test_threshold_engine_evaluation():
    """Verify ThresholdEngine triggers alerts when metrics exceed thresholds."""
    engine = ThresholdEngine()
    # Mock snapshot with high CPU & RAM
    snap = MonitoringSnapshot(
        cpu=CPUMetrics(usage_percent=95.0, logical_cores=4, frequency_mhz=2100),
        memory=MemoryMetrics(total_mb=8192, used_mb=7500, available_mb=692, percent=91.5),
    )
    alerts = engine.evaluate(snap)
    assert len(alerts) >= 1
    categories = {a.category for a in alerts}
    assert "cpu" in categories or "memory" in categories
