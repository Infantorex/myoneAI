"""Self-contained test and demonstration suite for Phase 9 Monitoring & Alerts.

Can be run directly:
    python -m app.monitoring.test_monitoring
or via pytest.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

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


def test_cpu_metrics():
    """Verify CPU utilization and core count retrieval."""
    metrics = get_cpu_metrics(sample_interval=0.01)
    assert isinstance(metrics, CPUMetrics)
    assert 0.0 <= metrics.usage_percent <= 100.0
    assert metrics.logical_cores >= 1


def test_memory_metrics():
    """Verify RAM metrics retrieval."""
    metrics = get_memory_metrics()
    assert isinstance(metrics, MemoryMetrics)
    assert metrics.total_mb > 0
    assert metrics.used_mb >= 0
    assert 0.0 <= metrics.percent <= 100.0


def test_disk_metrics():
    """Verify disk storage telemetry."""
    metrics = get_disk_metrics()
    assert isinstance(metrics, DiskMetrics)
    assert metrics.total_gb > 0
    assert 0.0 <= metrics.percent <= 100.0


def test_battery_metrics():
    """Verify battery telemetry without crashing on desktops."""
    metrics = get_battery_metrics()
    assert isinstance(metrics, BatteryMetrics)
    assert 0.0 <= metrics.percent <= 100.0
    assert isinstance(metrics.power_plugged, bool)


def test_network_metrics():
    """Verify basic network telemetry."""
    metrics = get_network_metrics(check_latency=False)
    assert isinstance(metrics, NetworkMetrics)
    assert isinstance(metrics.is_connected, bool)
    assert metrics.hostname is not None


def test_process_metrics():
    """Verify process monitoring."""
    procs = get_top_processes(limit=3, sort_by="memory")
    assert isinstance(procs, list)
    if procs:
        assert isinstance(procs[0], ProcessItem)
        assert procs[0].pid >= 0
        assert procs[0].name != ""

    summary = get_process_metrics(limit=3)
    assert isinstance(summary, ProcessMetrics)


def test_monitoring_snapshot():
    """Verify aggregate snapshot generation and formatting."""
    manager = MonitoringManager()
    snap = manager.get_snapshot_sync(include_processes=True, sample_interval=0.01)
    assert isinstance(snap, MonitoringSnapshot)
    assert snap.cpu is not None
    assert snap.memory is not None
    assert snap.disk is not None
    assert snap.network is not None

    data_dict = snap.to_dict()
    assert "cpu_percent" in data_dict
    assert "memory_percent" in data_dict
    assert "disk_percent" in data_dict

    summary_str = snap.to_summary()
    assert "CPU:" in summary_str
    assert "RAM:" in summary_str


def test_missing_battery_graceful():
    """Verify missing battery sensor fallback does not crash."""
    with patch("psutil.sensors_battery", return_value=None):
        batt = get_battery_metrics()
        assert batt.is_available is False
        assert batt.power_plugged is True


def test_missing_network_graceful():
    """Verify network collector handles connection exceptions gracefully."""
    with patch("socket.socket", side_effect=Exception("No network")):
        with patch("socket.gethostbyname", side_effect=Exception("No DNS")):
            net = get_network_metrics(check_latency=False)
            assert net.is_connected is False


def test_threshold_detection_warnings_and_critical():
    """Verify threshold evaluation for warning and critical conditions."""
    custom_settings = Settings(
        cpu_warning_threshold=80.0,
        cpu_critical_threshold=95.0,
        memory_warning_threshold=75.0,
        memory_critical_threshold=90.0,
        battery_low_threshold=20.0,
        battery_critical_threshold=10.0,
    )
    engine = ThresholdEngine(settings=custom_settings)

    # 1. Normal Snapshot
    normal_snap = MonitoringSnapshot(
        cpu=CPUMetrics(usage_percent=30.0, logical_cores=4),
        memory=MemoryMetrics(total_mb=8192, used_mb=4096, available_mb=4096, percent=50.0),
        battery=BatteryMetrics(percent=80.0, power_plugged=False, is_available=True),
    )
    assert len(engine.evaluate(normal_snap)) == 0

    # 2. Warning Snapshot (CPU 85%, RAM 78%, Battery 18%)
    warning_snap = MonitoringSnapshot(
        cpu=CPUMetrics(usage_percent=85.0, logical_cores=4),
        memory=MemoryMetrics(total_mb=8192, used_mb=6389, available_mb=1803, percent=78.0),
        battery=BatteryMetrics(percent=18.0, power_plugged=False, is_available=True),
    )
    alerts = engine.evaluate(warning_snap)
    assert len(alerts) == 3
    assert all(a.level == AlertLevel.WARNING for a in alerts)

    # 3. Critical Snapshot (CPU 98%, RAM 95%, Battery 8%)
    critical_snap = MonitoringSnapshot(
        cpu=CPUMetrics(usage_percent=98.0, logical_cores=4),
        memory=MemoryMetrics(total_mb=8192, used_mb=7782, available_mb=410, percent=95.0),
        battery=BatteryMetrics(percent=8.0, power_plugged=False, is_available=True),
    )
    crit_alerts = engine.evaluate(critical_snap)
    assert len(crit_alerts) == 3
    assert all(a.level == AlertLevel.CRITICAL for a in crit_alerts)


def test_alert_cooldown_deduplication():
    """Verify duplicate alerts are suppressed during cooldown period."""
    custom_settings = Settings(alert_cooldown_seconds=300)
    mgr = AlertManager(settings=custom_settings)

    alert1 = SystemAlert(
        level=AlertLevel.WARNING,
        category="memory",
        metric_name="RAM Usage",
        current_value=85.0,
        threshold=80.0,
        message="RAM high",
        tamil_message="RAM அதிகம்",
    )

    now = 1000.0
    # First detection -> allowed
    dispatched1 = mgr.process_alerts([alert1], current_time=now)
    assert len(dispatched1) == 1

    # Immediate second detection -> suppressed
    dispatched2 = mgr.process_alerts([alert1], current_time=now + 60.0)
    assert len(dispatched2) == 0

    # 301 seconds later -> allowed
    dispatched3 = mgr.process_alerts([alert1], current_time=now + 301.0)
    assert len(dispatched3) == 1


def test_slow_laptop_diagnosis():
    """Verify performance diagnosis identifies RAM and CPU bottlenecks."""
    custom_settings = Settings(
        cpu_warning_threshold=80.0,
        memory_warning_threshold=80.0,
    )
    manager = MonitoringManager(settings=custom_settings)

    diag = asyncio.run(manager.diagnose_slow_system())
    assert "status" in diag
    assert "observed_metrics" in diag
    assert "diagnosis_summary" in diag
    assert "recommendations" in diag


def test_intent_parsing_and_tool_integration():
    """Verify voice/text intents map to Phase 9 tools and tools execute safely."""
    # Test intent detection
    call1 = parse_tool_intent("Jarvis, how is my laptop?")
    assert call1 is not None and call1.tool == "get_system_status"

    call2 = parse_tool_intent("Check RAM")
    assert call2 is not None and call2.tool in ("get_ram_usage", "get_memory_status")

    call3 = parse_tool_intent("Check battery")
    assert call3 is not None and call3.tool == "get_battery_status"

    call4 = parse_tool_intent("Which app is using the most memory?")
    assert call4 is not None and call4.tool == "get_top_processes"

    call5 = parse_tool_intent("Why is my laptop slow?")
    assert call5 is not None and call5.tool == "diagnose_system_performance"

    # Test tool execution from registry
    for tool_name in [
        "get_system_status",
        "get_cpu_status",
        "get_memory_status",
        "get_disk_status",
        "get_battery_status",
        "get_network_status",
        "get_top_processes",
        "diagnose_system_performance",
    ]:
        entry = tool_registry.get(tool_name)
        assert entry is not None, f"Tool {tool_name} not found in ToolRegistry"
        schema, handler = entry
        res = handler()
        assert res.success is True, f"Tool {tool_name} execution failed: {res.message}"


def run_all():
    """Run all tests sequentially and report result."""
    print("=" * 60)
    print("Running Phase 9 Monitoring & Alerts Test Suite")
    print("=" * 60)

    tests = [
        ("CPU Metrics", test_cpu_metrics),
        ("RAM Metrics", test_memory_metrics),
        ("Disk Metrics", test_disk_metrics),
        ("Battery Metrics", test_battery_metrics),
        ("Network Metrics", test_network_metrics),
        ("Process Metrics", test_process_metrics),
        ("Monitoring Snapshot", test_monitoring_snapshot),
        ("Missing Battery Fallback", test_missing_battery_graceful),
        ("Missing Network Fallback", test_missing_network_graceful),
        ("Threshold Detection (Warning & Critical)", test_threshold_detection_warnings_and_critical),
        ("Alert Cooldown & Deduplication", test_alert_cooldown_deduplication),
        ("Slow Laptop Diagnosis", test_slow_laptop_diagnosis),
        ("Intent Parsing & Tool Integration", test_intent_parsing_and_tool_integration),
    ]

    passed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as exc:
            print(f"  [FAIL] {name}: {exc}")
            raise

    print("=" * 60)
    print(f"All {passed}/{len(tests)} Phase 9 tests passed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    run_all()
