"""Unit tests for logging system and sensitive data redaction (app/core/logging_config.py).
"""

import logging
from pathlib import Path
from app.core.logging_config import setup_logging, get_logger, SensitiveDataFilter


def test_sensitive_data_filter():
    """Verify that sensitive patterns are redacted."""
    filter_inst = SensitiveDataFilter()

    # Direct text masking
    masked = filter_inst.mask_sensitive_text("api_key='secret123' and password='password456'")
    assert "secret123" not in masked
    assert "password456" not in masked
    assert "[REDACTED]" in masked

    # Bearer token masking
    bearer_masked = filter_inst.mask_sensitive_text("Authorization: Bearer my_secret_token_abc")
    assert "my_secret_token_abc" not in bearer_masked
    assert "[REDACTED]" in bearer_masked


def test_setup_logging_with_file(tmp_path: Path):
    """Verify logger creates rotating file and records messages."""
    log_file = tmp_path / "test_jarvis.log"
    logger = setup_logging(log_level="DEBUG", log_file=log_file)

    logger.info("Starting test log message")
    logger.warning("Warning with api_key=super_secret_key_123")

    # Ensure log file was written
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Starting test log message" in content
    assert "super_secret_key_123" not in content
    assert "[REDACTED]" in content


def test_get_logger_namespace():
    """Verify child logger namespacing."""
    child_logger = get_logger("custom_service")
    assert child_logger.name == "myoneAI.custom_service"
