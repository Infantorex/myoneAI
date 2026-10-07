"""Privacy filter and sensitive credential validator for AI Memory System (Phase 7).

Ensures passwords, API keys, bearer tokens, OTPs, and financial data are never stored in memory.
"""

import logging
import re
from typing import Tuple

logger = logging.getLogger("myoneAI.memory.privacy")

# Regex patterns for sensitive credential detection
SENSITIVE_PATTERNS = [
    # API keys, Secret keys, Tokens
    re.compile(r"(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|bearer\s+[a-zA-Z0-9_\-\.]{15,})\b"),
    re.compile(r"(?i)\b(?:sk-[a-zA-Z0-9]{20,}|AIza[0-9A-Za-z-_]{35}|ghp_[a-zA-Z0-9]{36})\b"),
    # Passwords & PINs
    re.compile(r"(?i)\b(?:password|passwd|passcode|pin\s*code|secret\s*code)\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bmy\s+(?:password|pin|passcode)\s+is\s+\S+"),
    # OTP & Verification codes
    re.compile(r"(?i)\b(?:otp|one[_-]?time[_-]?password|verification\s*code)\s*[:=]?\s*\d{4,8}\b"),
    # Credit / Debit Cards (Luhn candidate 13-19 digits with separators)
    re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    re.compile(r"\b(?:\d{4}[-\s]?\d{6}[-\s]?\d{5})\b"),
    # CVV / CVC
    re.compile(r"(?i)\b(?:cvv|cvc|security\s*code)\s*[:=]?\s*\d{3,4}\b"),
    # Bank Account / Routing / IBAN
    re.compile(r"(?i)\b(?:bank\s*account|account\s*number|iban|routing\s*number)\s*[:=]?\s*[A-Z0-9]{8,34}\b"),
    # Private Keys / RSA / PEM
    re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----"),
]

PRIVACY_REJECTION_MESSAGE = "I can't save sensitive credentials or private security information."
PRIVACY_REJECTION_MESSAGE_TAMIL = "பாதுகாப்பு காரணங்களால் கடவுச்சொற்கள், ரகசிய குறியீடுகள் அல்லது நிதி விவரங்களை நினைவில் வைக்க முடியாது."


class SensitiveDataMemoryError(Exception):
    """Raised when an attempt is made to store sensitive or private security information."""
    pass


def is_sensitive(text: str) -> bool:
    """Check if the provided text contains sensitive credentials or financial information."""
    if not text or not isinstance(text, str):
        return False
    
    clean_text = text.strip()
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(clean_text):
            return True
    return False


def validate_memory_content(key: str, value: str) -> Tuple[bool, str]:
    """Validate memory key and value against privacy policies.

    Args:
        key: The key/identifier string.
        value: The value/fact string.

    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    if is_sensitive(key) or is_sensitive(value):
        logger.warning("Memory storage rejected by privacy filter (sensitive content detected).")
        return False, PRIVACY_REJECTION_MESSAGE

    if not key.strip() or not value.strip():
        return False, "Memory key and value cannot be empty."

    return True, ""
