"""Structured security audit logger for PC Assistant Tools (Phase 8).

Records tool invocations, permission decisions, and execution outcomes with strict credential masking.
"""

import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, Optional

from app.core.logging_config import SensitiveDataFilter

logger = logging.getLogger("myoneAI.security.audit")


class SecurityAuditLogger:
    """Logs tool execution and access control decisions securely."""

    def __init__(self, log_file_path: Optional[Path] = None) -> None:
        self.log_file_path = log_file_path
        self._filter = SensitiveDataFilter()

    def log_tool_decision(
        self,
        tool_name: str,
        permission_level: str,
        status: Optional[str] = None,
        details: Optional[str] = None,
        duration_sec: Optional[float] = None,
        result: Optional[str] = None,
    ) -> None:
        """Record an access decision and execution result.

        Args:
            tool_name: Registered name of the tool.
            permission_level: Permission tier (SAFE, CONFIRM, BLOCKED).
            status: Outcome status (e.g. 'success', 'rejected', 'failed', 'pending_confirmation').
            details: Sanitized contextual note (zero secrets).
            duration_sec: Execution duration in seconds.
            result: Alias for status.
        """
        outcome_status = (status or result or "UNKNOWN").upper()
        dur_str = f" duration={duration_sec:.3f}s" if duration_sec is not None else ""
        sanitized_details = self._filter.mask_sensitive_text(details) if details else ""
        det_str = f" details=\"{sanitized_details}\"" if sanitized_details else ""

        log_msg = f"tool={tool_name} permission={permission_level.upper()} result={outcome_status.lower()}{dur_str}{det_str}"



        if outcome_status.lower() in ("success", "allowed"):
            logger.info("[AUDIT] %s", log_msg)
        elif outcome_status.lower() in ("rejected", "blocked", "permission_denied"):
            logger.warning("[AUDIT-BLOCKED] %s", log_msg)
        elif outcome_status.lower() in ("failed", "error"):
            logger.error("[AUDIT-ERROR] %s", log_msg)
        else:
            logger.info("[AUDIT] %s", log_msg)


        if self.log_file_path:
            try:
                self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.log_file_path, "a", encoding="utf-8") as f:
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"{timestamp} [AUDIT] {log_msg}\n")
            except Exception as e:
                logger.debug("Failed writing to audit file %s: %s", self.log_file_path, e)


# Global audit logger singleton
audit_logger = SecurityAuditLogger()

