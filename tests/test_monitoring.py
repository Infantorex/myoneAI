"""Pytest test suite for Phase 9: Lightweight System Monitoring & Alerts."""

import asyncio
import time
from unittest.mock import MagicMock, patch
import pytest

from app.core.config import Settings
from app.monitoring.alerts import AlertManager
from app.monitoring.battery import get_battery_metrics
from app.monitoring.cpu import get_cpu_metrics
from app.monitoring.disk import get_disk_metrics
from app.monitoring.manager import MonitoringManager
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
from app.monitoring.thresholds import ThresholdEngine
from app.tools.intent import parse_tool_intent
from app.tools.registry import tool_registry


def test_cpu_metrics_live():
    """Verify live CPU metrics collection."""
    metrics = get_cpu_metrics(sample_interval=0.01)
    assert isinstance(metrics, CPUMetrics)
    assert 0.0 <= metrics.usage_percent <= 100.0
    assert metrics.logical_cores >= 1
    d = metrics.to_dict()
    assert "usage_percent" in d
    assert "logical_cores" in d


def test_memory_metrics_live():
    """Verify live RAM metrics collection."""
    metrics = get_memory_metrics()
    assert isinstance(metrics, MemoryMetrics)
    assert metrics.total_mb > 0
    assert metrics.used_mb >= 0
    assert 0.0 <= metrics.percent <= 100.0
    d = metrics.to_dict()
    assert "total_mb" in d
    assert "percent" in d


def test_disk_metrics_live():
    """Verify live disk storage metrics."""
    metrics = get_disk_metrics()
    assert isinstance(metrics, DiskMetrics)
    assert metrics.total_gb > 0
    assert metrics.free_gb >= 0
    assert 0.0 <= metrics.percent <= 100.0
    d = metrics.to_dict()
    assert "total_gb" in d
    assert "mount_point" in d


def test_battery_metrics_live():
    """Verify live battery telemetry."""
    metrics = get_battery_metrics()
    assert isinstance(metrics, BatteryMetrics)
    assert 0.0 <= metrics.percent <= 100.0
    assert isinstance(metrics.power_plugged, bool)
    assert isinstance(metrics.is_available, bool)


def test_battery_missing_fallback():
    """Verify graceful handling when no battery sensor is available."""
    with patch("psutil.sensors_battery", return_value=None):
        metrics = get_battery_metrics()
        assert metrics.is_available is False
        assert metrics.power_plugged is True
        assert metrics.percent == 100.0


def test_network_metrics_live():
    """Verify live network metrics."""
    metrics = get_network_metrics(check_latency=False)
    assert isinstance(metrics, NetworkMetrics)
    assert isinstance(metrics.is_connected, bool)
    assert metrics.hostname != ""


def test_network_missing_fallback():
    """Verify graceful fallback when network resolution throws exceptions."""
    with patch("socket.socket", side_effect=Exception("Socket error")):
        with patch("socket.gethostbyname", side_effect=Exception("DNS error")):
            metrics = get_network_metrics(check_latency=False)
            assert metrics.is_connected is False


def test_process_metrics_live():
    """Verify process list retrieval on demand."""
    procs = get_top_processes(limit=3, sort_by="memory")
    assert isinstance(procs, list)
    if procs:
        item = procs[0]
        assert isinstance(item, ProcessItem)
        assert item.pid >= 0
        assert item.name != ""
        assert item.memory_mb >= 0

    procs_cpu = get_top_processes(limit=3, sort_by="cpu")
    assert isinstance(procs_cpu, list)

    summary = get_process_metrics(limit=3)
    assert isinstance(summary, ProcessMetrics)
    assert len(summary.top_memory) <= 3
    assert len(summary.top_cpu) <= 3


def test_monitoring_snapshot_assembly():
    """Verify full snapshot creation, serialization, and summary string."""
    manager = MonitoringManager()
    snapshot = manager.get_snapshot_sync(include_processes=True, process_limit=3, sample_interval=0.01)

    assert isinstance(snapshot, MonitoringSnapshot)
    assert snapshot.cpu is not None
    assert snapshot.memory is not None
    assert snapshot.disk is not None
    assert snapshot.network is not None

    data = snapshot.to_dict()
    assert "timestamp" in data
    assert "cpu_percent" in data
    assert "memory_percent" in data
    assert "disk_percent" in data
    assert "battery_percent" in data
    assert "processes" in data

    summary = snapshot.to_summary()
    assert "CPU:" in summary
    assert "RAM:" in summary


def test_threshold_engine_evaluation():
    """Verify warning and critical threshold detections across all sensors."""
    settings = Settings(
        cpu_warning_threshold=80.0,
        cpu_critical_threshold=95.0,
        memory_warning_threshold=80.0,
        memory_critical_threshold=90.0,
        disk_warning_threshold=85.0,
        disk_critical_threshold=95.0,
        battery_low_threshold=20.0,
        battery_critical_threshold=10.0,
    )
    engine = ThresholdEngine(settings=settings)

    # 1. Normal State
    normal_snap = MonitoringSnapshot(
        cpu=CPUMetrics(usage_percent=40.0, logical_cores=4),
        memory=MemoryMetrics(total_mb=8192, used_mb=4000, available_mb=4192, percent=50.0),
        disk=DiskMetrics(total_gb=500, used_gb=200, free_gb=300, percent=40.0),
        battery=BatteryMetrics(percent=85.0, power_plugged=False, is_available=True),
    )
    alerts = engine.evaluate(normal_snap)
    assert len(alerts) == 0

    # 2. Warning Level State
    warning_snap = MonitoringSnapshot(
        cpu=CPUMetrics(usage_percent=85.0, logical_cores=4),
        memory=MemoryMetrics(total_mb=8192, used_mb=6700, available_mb=1492, percent=82.0),
        disk=DiskMetrics(total_gb=500, used_gb=430, free_gb=70, percent=86.0),
        battery=BatteryMetrics(percent=18.0, power_plugged=False, is_available=True),
    )
    warn_alerts = engine.evaluate(warning_snap)
    assert len(warn_alerts) == 4
    assert all(a.level == AlertLevel.WARNING for a in warn_alerts)
    categories = {a.category for a in warn_alerts}
    assert categories == {"cpu", "memory", "disk", "battery"}

    # 3. Critical Level State
    critical_snap = MonitoringSnapshot(
        cpu=CPUMetrics(usage_percent=98.0, logical_cores=4),
        memory=MemoryMetrics(total_mb=8192, used_mb=7600, available_mb=592, percent=93.0),
        disk=DiskMetrics(total_gb=500, used_gb=480, free_gb=20, percent=96.0),
        battery=BatteryMetrics(percent=8.0, power_plugged=False, is_available=True),
    )
    crit_alerts = engine.evaluate(critical_snap)
    assert len(crit_alerts) == 4
    assert all(a.level == AlertLevel.CRITICAL for a in crit_alerts)


def test_alert_manager_cooldown_and_handlers():
    """Verify AlertManager cooldown deduplication and callback dispatch."""
    settings = Settings(alert_cooldown_seconds=300)
    alert_mgr = AlertManager(settings=settings)

    dispatched_events = []
    def alert_handler(a: SystemAlert):
        dispatched_events.append(a)

    alert_mgr.register_handler(alert_handler)

    alert = SystemAlert(
        level=AlertLevel.WARNING,
        category="memory",
        metric_name="RAM Usage",
        current_value=85.0,
        threshold=80.0,
        message="RAM high",
        tamil_message="RAM அதிகம்",
    )

    now = 1000.0
    # First alert should dispatch
    res1 = alert_mgr.process_alerts([alert], current_time=now)
    assert len(res1) == 1
    assert len(dispatched_events) == 1

    # Immediate second alert should be suppressed
    res2 = alert_mgr.process_alerts([alert], current_time=now + 50.0)
    assert len(res2) == 0
    assert len(dispatched_events) == 1

    # After 301 seconds, alert should dispatch again
    res3 = alert_mgr.process_alerts([alert], current_time=now + 301.0)
    assert len(res3) == 1
    assert len(dispatched_events) == 2

    # Unregister handler
    alert_mgr.unregister_handler(alert_handler)
    res4 = alert_mgr.process_alerts([alert], current_time=now + 700.0)
    assert len(res4) == 1
    assert len(dispatched_events) == 2  # Handlers list updated


@pytest.mark.asyncio
async def test_monitoring_manager_async_snapshot():
    """Verify asynchronous snapshot and check_and_alert in MonitoringManager."""
    manager = MonitoringManager()
    snap = await manager.get_snapshot(include_processes=False, sample_interval=0.01)
    assert isinstance(snap, MonitoringSnapshot)
    assert snap.cpu is not None

    alerts = await manager.check_and_alert()
    assert isinstance(alerts, list)


@pytest.mark.asyncio
async def test_slow_laptop_diagnosis():
    """Verify diagnose_slow_system returns structured metrics and recommendations."""
    manager = MonitoringManager()
    diag = await manager.diagnose_slow_system(process_limit=3)

    assert "status" in diag
    assert "observed_metrics" in diag
    assert "diagnosis_summary" in diag
    assert "tamil_summary" in diag
    assert "recommendations" in diag
    assert "tamil_recommendations" in diag
    assert isinstance(diag["recommendations"], list)


def test_intent_parsing_monitoring_commands():
    """Verify natural language queries in Tamil and English map to appropriate tools."""
    queries = [
        ("Jarvis, how is my laptop?", "get_system_status"),
        ("How is my laptop?", "get_system_status"),
        ("Check my system", "get_system_status"),
        ("லேப்டாப் நிலை என்ன?", "get_system_status"),
        ("Check RAM", "get_ram_usage"),
        ("How much RAM am I using?", "get_ram_usage"),
        ("RAM பயன்பாடு", "get_ram_usage"),
        ("Jarvis, what's my CPU usage?", "get_cpu_usage"),
        ("Check CPU", "get_cpu_usage"),
        ("CPU பயன்பாடு எவ்வளவு?", "get_cpu_usage"),
        ("How much storage do I have?", "get_disk_usage"),
        ("Check disk space", "get_disk_usage"),
        ("வட்டு சேமிப்பகம்", "get_disk_usage"),
        ("Jarvis, check battery", "get_battery_status"),
        ("Battery status", "get_battery_status"),
        ("பேட்டரி எவ்வளவு?", "get_battery_status"),
        ("Am I connected to the internet?", "get_network_status"),
        ("Check network connection", "get_network_status"),
        ("இணைய இணைப்பு இருக்கா?", "get_network_status"),
        ("Which app is using the most RAM?", "get_top_processes"),
        ("What's using the most memory?", "get_top_processes"),
        ("எந்த ஆப் அதிக RAM பயன்படுத்துகிறது?", "get_top_processes"),
        ("Why is my laptop slow?", "diagnose_system_performance"),
        ("Laptop slow", "diagnose_system_performance"),
        ("லேப்டாப் ஏன் ஸ்லோவா இருக்கு?", "diagnose_system_performance"),
    ]

    for user_input, expected_tool in queries:
        call = parse_tool_intent(user_input)
        assert call is not None, f"Failed to match intent for: '{user_input}'"
        assert call.tool == expected_tool, f"Expected {expected_tool} for '{user_input}', got {call.tool}"


def test_monitoring_tools_in_registry():
    """Verify all Phase 9 monitoring tools are registered as SAFE in ToolRegistry."""
    expected_tools = [
        "get_system_status",
        "get_system_info",
        "get_cpu_status",
        "get_cpu_usage",
        "get_memory_status",
        "get_ram_usage",
        "get_disk_status",
        "get_disk_usage",
        "get_battery_status",
        "get_network_status",
        "get_top_processes",
        "diagnose_system_performance",
    ]

    for tool_name in expected_tools:
        entry = tool_registry.get(tool_name)
        assert entry is not None, f"Tool {tool_name} is not registered"
        schema, handler = entry
        assert schema.permission.value.lower() == "safe", f"Tool {tool_name} should be SAFE"

        # Execute handler
        result = handler()
        assert result.success is True, f"Tool {tool_name} failed: {result.message}"
        assert result.data is not None
