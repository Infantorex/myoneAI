"""Cryptographic authentication and HMAC-SHA256 request signing for Cloud Communication (Phase 12).

Guarantees integrity, non-repudiation, and constant-time token comparison between Laptop and Cloud.
"""

import hashlib
import hmac
import json
import logging
import secrets
from typing import Any, Dict, Optional

from app.cloud.errors import CloudAuthenticationError
from app.cloud.protocol import CloudMessage

logger = logging.getLogger("myoneAI.cloud.auth")


def canonicalize_payload(payload: Dict[str, Any]) -> str:
    """Produce a deterministic, key-sorted JSON representation of message payload."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_signature(secret_key: str, message: CloudMessage) -> str:
    """Calculate HMAC-SHA256 hex signature over the canonical message fields.

    Fields signed: id, type, timestamp, device_id, status, payload.
    """
    if not secret_key:
        raise CloudAuthenticationError("Cannot compute signature with an empty secret key.")

    status_str = message.status or ""
    payload_str = canonicalize_payload(message.payload)
    
    # Create canonical signing string
    data_to_sign = f"{message.id}|{message.type}|{message.timestamp:.4f}|{message.device_id}|{status_str}|{payload_str}"
    
    mac = hmac.new(
        secret_key.encode("utf-8"),
        data_to_sign.encode("utf-8"),
        hashlib.sha256,
    )
    return mac.hexdigest()


def sign_message(secret_key: str, message: CloudMessage) -> CloudMessage:
    """Attach computed HMAC-SHA256 signature to message."""
    message.signature = compute_signature(secret_key, message)
    return message


def verify_message_signature(secret_key: str, message: CloudMessage) -> bool:
    """Verify incoming message signature using constant-time comparison.

    Raises:
        CloudAuthenticationError: If signature is missing or invalid.
    """
    if not message.signature:
        raise CloudAuthenticationError(f"Missing HMAC signature for message '{message.id}'.")

    expected_sig = compute_signature(secret_key, message)
    if not secrets.compare_digest(message.signature, expected_sig):
        logger.warning("HMAC signature mismatch on message ID '%s'", message.id)
        raise CloudAuthenticationError(f"Invalid HMAC signature for message '{message.id}'.")

    return True


def generate_device_token() -> str:
    """Generate a cryptographically secure 256-bit authentication token."""
    return secrets.token_hex(32)
