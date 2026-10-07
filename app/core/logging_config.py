"""Structured logging configuration for myoneAI / Tamil JARVIS.

Provides rotating file logging and console logging with automatic sensitive data masking.
"""

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


# Sensitive patterns to redact from logs
SENSITIVE_PATTERNS = [
    re.compile(r"((?:api[_-]?)?key\s*[:=]\s*['\"]?)([^'\"\s]+)", re.IGNORECASE),
    re.compile(r"(password\s*[:=]\s*['\"]?)([^'\"\s]+)", re.IGNORECASE),
    re.compile(r"(token\s*[:=]\s*['\"]?)([^'\"\s]+)", re.IGNORECASE),
    re.compile(r"(secret\s*[:=]\s*['\"]?)([^'\"\s]+)", re.IGNORECASE),
    re.compile(r"(bearer\s+)([a-zA-Z0-9_\-\.]+)", re.IGNORECASE),
    re.compile(r"\b(sk-[a-zA-Z0-9_\-]{8,})\b", re.IGNORECASE),
]



class SensitiveDataFilter(logging.Filter):
    """Filter that masks API keys, passwords, and tokens in log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if record.args:
                record.msg = record.getMessage()
                record.args = None
            if isinstance(record.msg, str):
                record.msg = self.mask_sensitive_text(record.msg)
        except Exception:
            pass
        return True

    @staticmethod
    def mask_sensitive_text(text: str) -> str:
        """Replace sensitive patterns with a masked placeholder."""
        for pattern in SENSITIVE_PATTERNS:
            text = pattern.sub(r"\1[REDACTED]", text)
        return text



def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path | str] = None,
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB per file
    backup_count: int = 3,
) -> logging.Logger:
    """Configure the root logger with rotation and console stream handlers.

    Args:
        log_level: Desired log level string (e.g. 'DEBUG', 'INFO', 'WARNING').
        log_file: Path to the log file. If None, only console logging is used.
        max_bytes: Max log file size before rotation (default 5MB).
        backup_count: Number of rotated log files to retain (default 3).

    Returns:
        Configured root logger instance.
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger = logging.getLogger("myoneAI")
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if root_logger.handlers:
        root_logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s:%(module)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    filter_instance = SensitiveDataFilter()

    # 1. Console Handler (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(filter_instance)
    root_logger.addHandler(console_handler)

    # 2. Rotating File Handler
    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            filename=str(file_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(filter_instance)
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'myoneAI' namespace."""
    return logging.getLogger(f"myoneAI.{name}")
