"""Unit tests for Cloud HMAC Signing & Authentication (Phase 12)."""

import pytest

from app.cloud.authentication import (
    compute_signature,
    generate_device_token,
    sign_message,
    verify_message_signature,
)
from app.cloud.errors import CloudAuthenticationError
from app.cloud.protocol import CloudMessage, MessageType


def test_hmac_signature_calculation_and_verification():
    """Test valid signature signing and verification."""
    secret = "my-secret-cloud-key-321"
    msg = CloudMessage(
        id="sig-test-1",
        type=MessageType.COMMAND.value,
        timestamp=1775570000.0,
        device_id="laptop-abc",
        payload={"tool": "get_system_status", "arguments": {}},
    )

    sign_message(secret, msg)
    assert msg.signature is not None
    assert len(msg.signature) == 64  # SHA-256 hex string

    # Verification passes
    assert verify_message_signature(secret, msg) is True


def test_hmac_tampered_payload_rejection():
    """Test that modifying payload invalidates the signature."""
    secret = "my-secret-cloud-key-321"
    msg = CloudMessage(
        id="sig-test-tamper",
        type=MessageType.COMMAND.value,
        timestamp=1775570000.0,
        device_id="laptop-abc",
        payload={"tool": "get_system_status", "arguments": {}},
    )

    sign_message(secret, msg)

    # Tamper with payload
    msg.payload["tool"] = "delete_file"

    with pytest.raises(CloudAuthenticationError, match="Invalid HMAC signature"):
        verify_message_signature(secret, msg)


def test_hmac_wrong_secret_rejection():
    """Test verification with mismatched secret key."""
    msg = CloudMessage(
        id="sig-test-key",
        type=MessageType.COMMAND.value,
        timestamp=1775570000.0,
        device_id="laptop-abc",
        payload={},
    )
    sign_message("correct-secret", msg)

    with pytest.raises(CloudAuthenticationError, match="Invalid HMAC signature"):
        verify_message_signature("wrong-secret", msg)


def test_hmac_missing_signature():
    """Test verification fails when signature is omitted."""
    msg = CloudMessage(
        id="sig-test-none",
        type=MessageType.COMMAND.value,
        timestamp=1775570000.0,
        device_id="laptop-abc",
        payload={},
        signature=None,
    )
    with pytest.raises(CloudAuthenticationError, match="Missing HMAC signature"):
        verify_message_signature("any-secret", msg)


def test_device_token_generation():
    """Test secure token generation."""
    token1 = generate_device_token()
    token2 = generate_device_token()
    assert len(token1) == 64
    assert len(token2) == 64
    assert token1 != token2
