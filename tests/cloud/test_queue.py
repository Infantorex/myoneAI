"""Unit tests for Offline Event Queue & Privacy Filters (Phase 12)."""

import pytest

from app.cloud.errors import CloudSecurityError
from app.cloud.protocol import CloudMessage
from app.cloud.queue import OfflineEventQueue


def test_offline_queue_fifo_order():
    """Test message queuing and FIFO dequeueing."""
    q = OfflineEventQueue(max_size=10)
    msg1 = CloudMessage(id="m1", payload={"status": "online"})
    msg2 = CloudMessage(id="m2", payload={"status": "busy"})

    q.enqueue(msg1)
    q.enqueue(msg2)
    assert q.size == 2

    assert q.dequeue().id == "m1"
    assert q.dequeue().id == "m2"
    assert q.is_empty


def test_offline_queue_max_size_eviction():
    """Test that queue evicts oldest message when full."""
    q = OfflineEventQueue(max_size=3)
    for i in range(5):
        q.enqueue(CloudMessage(id=f"msg-{i}", payload={"val": i}))

    assert q.size == 3
    # Items remaining should be msg-2, msg-3, msg-4
    assert q.dequeue().id == "msg-2"
    assert q.dequeue().id == "msg-3"
    assert q.dequeue().id == "msg-4"


def test_offline_queue_rejects_sensitive_data():
    """Test that events containing passwords or API keys are rejected."""
    q = OfflineEventQueue(max_size=10)

    # Password attempt
    with pytest.raises(CloudSecurityError, match="sensitive field 'password'"):
        q.enqueue(CloudMessage(id="bad-1", payload={"password": "secret_pass"}))

    # API key attempt
    with pytest.raises(CloudSecurityError, match="sensitive field 'api_key'"):
        q.enqueue(CloudMessage(id="bad-2", payload={"api_key": "AIzaSy..."}))

    # Raw audio attempt
    with pytest.raises(CloudSecurityError, match="sensitive field 'raw_audio'"):
        q.enqueue(CloudMessage(id="bad-3", payload={"raw_audio": "base64bytes..."}))
