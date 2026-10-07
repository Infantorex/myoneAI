"""Unit tests for state management and telemetry (app/core/state.py).
"""

from app.core.state import StateManager, AssistantState, ServiceStatus
from app.core.events import EventBus


def test_initial_state():
    """Verify initial state values."""
    mgr = StateManager()
    assert mgr.current_state == AssistantState.IDLE
    assert mgr.uptime_seconds >= 0


def test_state_transition():
    """Verify state transitions and state properties."""
    mgr = StateManager()
    mgr.set_state(AssistantState.LISTENING)
    assert mgr.current_state == AssistantState.LISTENING

    mgr.set_state(AssistantState.SPEAKING)
    assert mgr.current_state == AssistantState.SPEAKING


def test_service_status_tracking():
    """Verify service status management."""
    mgr = StateManager()
    assert mgr.get_service_status("voice") == ServiceStatus.STOPPED

    mgr.set_service_status("voice", ServiceStatus.RUNNING)
    assert mgr.get_service_status("voice") == ServiceStatus.RUNNING


def test_error_recording():
    """Verify error state recording."""
    mgr = StateManager()
    mgr.set_error("Test audio device missing")
    assert mgr.current_state == AssistantState.ERROR

    snap = mgr.get_snapshot()
    assert snap["last_error"] == "Test audio device missing"


def test_get_system_metrics_and_snapshot():
    """Verify metrics and full snapshot payload."""
    mgr = StateManager()
    metrics = mgr.get_system_metrics()
    assert "cpu_percent" in metrics
    assert "ram_percent" in metrics
    assert metrics["ram_total_mb"] > 0

    snapshot = mgr.get_snapshot()
    assert "state" in snapshot
    assert "uptime_seconds" in snapshot
    assert "services" in snapshot
    assert "metrics" in snapshot
