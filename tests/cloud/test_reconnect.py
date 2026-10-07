"""Unit tests for Reconnection Manager & Exponential Backoff (Phase 12)."""

from app.cloud.reconnect import ReconnectManager


def test_exponential_backoff_progression():
    """Test 2s -> 4s -> 8s -> 16s -> 32s -> max 60s progression."""
    rm = ReconnectManager(min_interval=2.0, max_interval=60.0, factor=2.0, jitter_ratio=0.0)

    # Attempt 0 -> initial min delay
    assert rm.get_next_delay() == 2.0

    # Failure 1
    d1 = rm.record_failure()
    assert d1 == 2.0
    assert rm.attempts == 1

    # Failure 2
    d2 = rm.record_failure()
    assert d2 == 4.0
    assert rm.attempts == 2

    # Failure 3
    d3 = rm.record_failure()
    assert d3 == 8.0

    # Failure 4
    d4 = rm.record_failure()
    assert d4 == 16.0

    # Failure 5
    d5 = rm.record_failure()
    assert d5 == 32.0

    # Failure 6 (capped at 60s)
    d6 = rm.record_failure()
    assert d6 == 60.0


def test_reconnect_manager_reset_on_success():
    """Test that recording success resets backoff attempts."""
    rm = ReconnectManager(min_interval=2.0, max_interval=60.0, factor=2.0, jitter_ratio=0.0)
    rm.record_failure()
    rm.record_failure()
    assert rm.attempts == 2

    rm.record_success()
    assert rm.attempts == 0
    assert rm.get_next_delay() == 2.0
