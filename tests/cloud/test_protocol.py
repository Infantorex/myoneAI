"""Unit tests for Cloud Message Protocol & Replay Protection (Phase 12)."""

import time
import pytest

from app.cloud.errors import CloudProtocolError, CloudReplayError
from app.cloud.protocol import CloudMessage, MessageType, ReplayProtection, ResponseStatus


def test_cloud_message_serialization():
    """Test message to/from dictionary serialization."""
    msg = CloudMessage(
        id="test-msg-001",
        type=MessageType.COMMAND.value,
        timestamp=1775570000.0,
        device_id="laptop-123",
        payload={"tool": "get_system_status", "arguments": {}},
        status=ResponseStatus.SUCCESS.value,
        signature="hex-sig-abc",
    )
    d = msg.to_dict()
    assert d["id"] == "test-msg-001"
    assert d["type"] == "command"
    assert d["device_id"] == "laptop-123"
    assert d["payload"]["tool"] == "get_system_status"
    assert d["signature"] == "hex-sig-abc"

    # Deserialize
    parsed = CloudMessage.from_dict(d)
    assert parsed.id == msg.id
    assert parsed.type == msg.type
    assert parsed.device_id == msg.device_id
    assert parsed.payload == msg.payload
    assert parsed.signature == msg.signature


def test_cloud_message_validation_errors():
    """Test that malformed dictionaries raise CloudProtocolError."""
    # Not a dict
    with pytest.raises(CloudProtocolError):
        CloudMessage.from_dict("not-a-dict")  # type: ignore

    # Missing ID
    with pytest.raises(CloudProtocolError):
        CloudMessage.from_dict({"type": "command", "timestamp": 123, "device_id": "d1", "payload": {}})

    # Missing type
    with pytest.raises(CloudProtocolError):
        CloudMessage.from_dict({"id": "id1", "timestamp": 123, "device_id": "d1", "payload": {}})

    # Invalid timestamp
    with pytest.raises(CloudProtocolError):
        CloudMessage.from_dict({"id": "id1", "type": "command", "timestamp": "invalid", "device_id": "d1", "payload": {}})

    # Missing device_id
    with pytest.raises(CloudProtocolError):
        CloudMessage.from_dict({"id": "id1", "type": "command", "timestamp": 123, "payload": {}})

    # Invalid payload (not a dict)
    with pytest.raises(CloudProtocolError):
        CloudMessage.from_dict({"id": "id1", "type": "command", "timestamp": 123, "device_id": "d1", "payload": "invalid"})


def test_replay_protection_fresh_message():
    """Test that fresh messages are accepted."""
    rp = ReplayProtection(max_drift_seconds=300.0)
    now = 1775570000.0
    msg = CloudMessage(
        id="fresh-msg-1",
        timestamp=now - 10.0,
        device_id="d1",
        payload={},
    )
    # Should not raise
    rp.validate_message(msg, current_time=now)


def test_replay_protection_expired_timestamp():
    """Test that expired messages (>300s old) are rejected."""
    rp = ReplayProtection(max_drift_seconds=300.0)
    now = 1775570000.0
    msg = CloudMessage(
        id="stale-msg-1",
        timestamp=now - 305.0,
        device_id="d1",
        payload={},
    )
    with pytest.raises(CloudReplayError, match="Message expired"):
        rp.validate_message(msg, current_time=now)


def test_replay_protection_future_timestamp():
    """Test that messages with excessive future timestamps are rejected."""
    rp = ReplayProtection(max_drift_seconds=300.0)
    now = 1775570000.0
    msg = CloudMessage(
        id="future-msg-1",
        timestamp=now + 45.0,  # >30s in future
        device_id="d1",
        payload={},
    )
    with pytest.raises(CloudReplayError, match="in the future"):
        rp.validate_message(msg, current_time=now)


def test_replay_protection_duplicate_id():
    """Test that replaying a seen message ID is rejected."""
    rp = ReplayProtection(max_drift_seconds=300.0)
    now = 1775570000.0
    msg = CloudMessage(
        id="duplicate-msg-id",
        timestamp=now - 5.0,
        device_id="d1",
        payload={},
    )
    # First time passes
    rp.validate_message(msg, current_time=now)

    # Second time raises replay error
    with pytest.raises(CloudReplayError, match="Duplicate message ID"):
        rp.validate_message(msg, current_time=now)
