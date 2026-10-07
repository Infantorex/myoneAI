"""Privacy and Data Leakage Compliance Tests."""

import logging
from pathlib import Path
import pytest

from app.core.config import get_settings
from app.core.logging_config import SensitiveDataFilter
from app.core.memory.privacy import validate_memory_content


def test_sensitive_data_not_in_memory_or_logs():
    """Verify SensitiveDataFilter and privacy validator protect user confidentiality."""
    filter_inst = SensitiveDataFilter()
    user_secret_input = "My login secret=Password!999 and token=token123456"
    sanitized = filter_inst.mask_sensitive_text(user_secret_input)
    assert "Password!999" not in sanitized
    assert "token123456" not in sanitized

    is_valid, err = validate_memory_content("user_creds", "password: SecretPassword")
    assert is_valid is False
    assert err is not None


def test_settings_does_not_expose_auth_tokens_in_repr():
    """Verify settings safe representation redacts sensitive API keys and cloud tokens."""
    settings = get_settings()
    safe_dict = settings.get_safe_dict()
    sensitive_keys = ["ai_api_key", "stt_api_key", "tts_api_key", "wake_word_api_key", "web_auth_token", "cloud_auth_token"]
    for key in sensitive_keys:
        val = safe_dict.get(key)
        if val is not None and str(val).strip():
            assert "..." in str(val) or "***" in str(val)
