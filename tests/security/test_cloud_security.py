"""Security tests for Phase 12 Cloud Protocol: Replay Defense, Token Invalidation, and Malformed Packets."""

import time
import pytest

from app.cloud.authentication import compute_signature, sign_message, verify_message_signature
from app.cloud.errors import CloudAuthenticationError, CloudReplayError, CloudSecurityError
from app.cloud.protocol import CloudMessage, MessageType, ReplayProtection
from app.cloud.queue import OfflineEventQueue


def test_cloud_replay_attack_prevention():
    """Verify replay protection rejects repeated message signatures and IDs."""
    replay = ReplayProtection(max_drift_seconds=300.0)
    now = time.time()
    msg = CloudMessage(id="msg_attacker_01", timestamp=now, device_id="dev_01", payload={})

    # First attempt: valid
    replay.validate_message(msg, current_time=now)

    # Second attempt (replay): must raise CloudReplayError
    with pytest.raises(CloudReplayError):
        replay.validate_message(msg, current_time=now)


def test_cloud_offline_queue_sensitive_data_rejection():
    """Verify offline queue strictly rejects queuing passwords, api keys, and credentials."""
    q = OfflineEventQueue(max_size=50)

    unsafe_payloads = [
        {"user_password": "PlaintextPassword123"},
        {"api_key": "sk-1234567890abcdef"},
        {"private_key": "-----BEGIN RSA PRIVATE KEY-----"},
        {"web_auth_token": "secret_bearer_token"},
    ]

    for p in unsafe_payloads:
        msg = CloudMessage(payload=p)
        with pytest.raises(CloudSecurityError):
            q.enqueue(msg)
