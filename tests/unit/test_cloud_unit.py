"""Unit tests for Phase 12 Cloud Protocol & Authentication."""

import time
import pytest

from app.cloud.authentication import compute_signature, sign_message, verify_message_signature
from app.cloud.errors import CloudAuthenticationError, CloudReplayError
from app.cloud.protocol import CloudMessage, MessageType, ReplayProtection
from app.cloud.queue import OfflineEventQueue


def test_hmac_signing_and_tamper_detection():
    """Verify HMAC-SHA256 signature generation and rejection of modified payloads."""
    secret = "unit_test_secret_key_12345"
    msg = CloudMessage(
        id="msg_001",
        type=MessageType.HEARTBEAT.value,
        timestamp=time.time(),
        device_id="dev_001",
        payload={"status": "online"},
    )
    signed = sign_message(secret, msg)
    assert signed.signature is not None
    assert verify_message_signature(secret, signed) is True

    # Tamper payload
    signed.payload["status"] = "tampered"
    with pytest.raises(CloudAuthenticationError):
        verify_message_signature(secret, signed)


def test_replay_protection_timestamp_and_duplicate():
    """Verify ReplayProtection rejects expired timestamps and duplicate message IDs."""
    replay = ReplayProtection(max_drift_seconds=300.0)
    now = time.time()

    # Valid message
    msg = CloudMessage(id="unique_01", timestamp=now, payload={})
    replay.validate_message(msg, current_time=now)

    # Duplicate message ID rejection
    with pytest.raises(CloudReplayError):
        replay.validate_message(msg, current_time=now)

    # Expired message rejection
    old_msg = CloudMessage(id="old_01", timestamp=now - 500.0, payload={})
    with pytest.raises(CloudReplayError):
        replay.validate_message(old_msg, current_time=now)
