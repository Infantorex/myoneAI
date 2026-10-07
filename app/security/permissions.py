"""Permission levels and centralized permission manager for PC Tools (Phase 8).

Categorizes actions into SAFE, CONFIRMATION_REQUIRED, and BLOCKED tiers, managing
confirmation tokens and timeout-based expiry.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple

from app.core.config import get_settings
from app.security.policies import (
    is_app_allowed,
    is_command_blocked,
    is_path_allowed,
    is_path_blocked,
    is_url_allowed,
)

logger = logging.getLogger("myoneAI.security.permissions")


class PermissionLevel(str, Enum):
    """Security tier for tools and system actions."""
    SAFE = "safe"                          # e.g., open approved app, get battery, volume up
    CONFIRMATION_REQUIRED = "confirmation" # e.g., delete file, close app, restart system
    BLOCKED = "blocked"                    # e.g., arbitrary shell execution, registry changes


@dataclass
class PendingConfirmation:
    """Represents a pending action requiring explicit user confirmation."""
    token: str
    tool_name: str
    arguments: Dict[str, Any]
    prompt_message: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0

    def is_expired(self) -> bool:
        """Check if confirmation window has expired."""
        return time.time() > self.expires_at


@dataclass
class ToolPermissionInfo:
    """Descriptor for tool permission level."""
    name: str
    level: PermissionLevel
    description: str = ""


class PermissionManager:
    """Central manager for tool permission validation and confirmation tokens."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._pending_confirmations: Dict[str, PendingConfirmation] = {}

    def get_permission(self, tool_name: str) -> ToolPermissionInfo:
        """Return ToolPermissionInfo with level for a given tool name."""
        level = self.get_tool_base_level(tool_name)
        return ToolPermissionInfo(name=tool_name, level=level)

    def is_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed under safe or confirm policies."""
        level = self.get_tool_base_level(tool_name)
        if level == PermissionLevel.BLOCKED:
            return False
        known_valid = {
            "open_application",
            "close_application",
            "open_website",
            "open_url",
            "search_web_browser",
            "list_directory",
            "open_directory",
            "open_file",
            "delete_file",
            "volume_up",
            "volume_down",
            "set_volume",
            "toggle_mute",
            "media_play_pause",
            "media_next",
            "media_previous",
            "take_screenshot",
            "get_battery_status",
            "get_cpu_usage",
            "get_ram_usage",
            "get_disk_usage",
            "get_system_info",
            "shutdown_system",
            "restart_system",
        }
        return tool_name in known_valid

    def requires_confirmation(self, tool_name: str) -> bool:
        """Check if a tool requires explicit user confirmation."""
        level = self.get_tool_base_level(tool_name)
        if level == PermissionLevel.CONFIRMATION_REQUIRED:
            return True
        known_safe = {
            "open_application",
            "open_website",
            "open_url",
            "search_web_browser",
            "list_directory",
            "open_directory",
            "open_file",
            "volume_up",
            "volume_down",
            "set_volume",
            "toggle_mute",
            "media_play_pause",
            "media_next",
            "media_previous",
            "take_screenshot",
            "get_battery_status",
            "get_cpu_usage",
            "get_ram_usage",
            "get_disk_usage",
            "get_system_info",
        }
        return tool_name not in known_safe

    def get_tool_base_level(self, tool_name: str) -> PermissionLevel:
        """Return default permission tier for a given tool name."""
        confirm_tools = {
            "close_application",
            "delete_file",
            "shutdown_system",
            "restart_system",
        }
        blocked_tools = {
            "execute_shell",
            "run_command",
            "eval_code",
            "modify_registry",
            "access_credentials",
        }

        if tool_name in blocked_tools:
            return PermissionLevel.BLOCKED
        if tool_name in confirm_tools:
            return PermissionLevel.CONFIRMATION_REQUIRED
        return PermissionLevel.SAFE

    def evaluate_tool_permission(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Tuple[PermissionLevel, str]:
        """Evaluate full permission tier based on tool name and runtime parameters.

        Returns:
            Tuple of (PermissionLevel, reason_string)
        """
        # 1. Check blocked tool names
        base_level = self.get_tool_base_level(tool_name)
        if base_level == PermissionLevel.BLOCKED:
            return PermissionLevel.BLOCKED, f"Tool '{tool_name}' is permanently blocked by security policy."

        # 2. Validate tool-specific parameters against policies
        if tool_name == "open_application":
            app_name = arguments.get("application", "")
            allowed, _ = is_app_allowed(app_name)
            if not allowed:
                return PermissionLevel.BLOCKED, f"Application '{app_name}' is not in the safe allowlist."

        elif tool_name in ("open_website", "open_url"):
            url = arguments.get("url", "")
            if not is_url_allowed(url):
                return PermissionLevel.BLOCKED, f"URL scheme or address '{url}' is forbidden."

        elif tool_name in ("list_directory", "open_directory", "open_file"):
            target_path = arguments.get("directory") or arguments.get("file_path") or arguments.get("path")
            if target_path and not is_path_allowed(target_path):
                return PermissionLevel.BLOCKED, f"Filesystem access to '{target_path}' is restricted."

        elif tool_name == "delete_file":
            file_path = arguments.get("file_path", "")
            if is_path_blocked(file_path):
                return PermissionLevel.BLOCKED, f"Deletion of system or credential path '{file_path}' is strictly blocked."
            if not is_path_allowed(file_path):
                return PermissionLevel.BLOCKED, f"File '{file_path}' is outside allowed user directories."
            return PermissionLevel.CONFIRMATION_REQUIRED, f"Deletion of '{file_path}' requires user confirmation."

        elif tool_name == "close_application":
            app_name = arguments.get("application", "")
            return PermissionLevel.CONFIRMATION_REQUIRED, f"Closing application '{app_name}' requires user confirmation."

        return base_level, "Action approved under SAFE policy."

    def create_pending_confirmation(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        prompt_message: str,
    ) -> PendingConfirmation:
        """Create and store a pending confirmation token."""
        token = str(uuid.uuid4())[:8]
        timeout = self.settings.tool_confirmation_timeout
        now = time.time()
        pending = PendingConfirmation(
            token=token,
            tool_name=tool_name,
            arguments=arguments,
            prompt_message=prompt_message,
            created_at=now,
            expires_at=now + timeout,
        )
        self._pending_confirmations[token] = pending
        # Also store under active tool_name for easy conversational matching
        self._pending_confirmations[tool_name] = pending
        logger.info("Created pending confirmation for '%s' (Token: %s, Timeout: %.1fs)", tool_name, token, timeout)
        return pending

    def get_pending_confirmation(self, identifier: Optional[str] = None) -> Optional[PendingConfirmation]:
        """Fetch active, unexpired pending confirmation by token or most recent."""
        self._cleanup_expired()

        if identifier and identifier in self._pending_confirmations:
            pending = self._pending_confirmations[identifier]
            if not pending.is_expired():
                return pending

        # Return latest pending if any
        for pending in reversed(list(self._pending_confirmations.values())):
            if not pending.is_expired():
                return pending
        return None

    def consume_confirmation(self, identifier: Optional[str] = None) -> Optional[PendingConfirmation]:
        """Consume and remove confirmed pending action."""
        pending = self.get_pending_confirmation(identifier)
        if pending:
            self._pending_confirmations.pop(pending.token, None)
            self._pending_confirmations.pop(pending.tool_name, None)
            logger.info("Consumed confirmation for '%s' (Token: %s)", pending.tool_name, pending.token)
            return pending
        return None

    def cancel_all_confirmations(self) -> None:
        """Cancel and purge all pending confirmations."""
        self._pending_confirmations.clear()
        logger.info("Purged all pending confirmations.")

    def _cleanup_expired(self) -> None:
        """Remove expired confirmation tokens."""
        expired_keys = [k for k, v in self._pending_confirmations.items() if v.is_expired()]
        for k in expired_keys:
            self._pending_confirmations.pop(k, None)


# Global permission manager singleton
permission_manager = PermissionManager()
