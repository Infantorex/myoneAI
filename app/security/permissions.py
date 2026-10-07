"""Permission levels and centralized permission checking.

Ensures the assistant cannot execute arbitrary commands or destructive actions without checks.
"""

from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass


class PermissionLevel(str, Enum):
    """Security tier for tools and system actions."""
    SAFE = "safe"                          # e.g., open chrome, get battery status
    CONFIRMATION_REQUIRED = "confirmation" # e.g., delete file, close app, shutdown
    HIGH_RISK = "high_risk"                # e.g., system config changes, registry edits
    BLOCKED = "blocked"                    # e.g., raw arbitrary shell commands


@dataclass
class ToolPermission:
    """Metadata for tool security categorization."""
    name: str
    level: PermissionLevel
    description: str


class PermissionManager:
    """Central manager for tool validation and access control."""

    def __init__(self) -> None:
        self._permissions: Dict[str, ToolPermission] = {
            "open_application": ToolPermission("open_application", PermissionLevel.SAFE, "Open a whitelisted application"),
            "close_application": ToolPermission("close_application", PermissionLevel.CONFIRMATION_REQUIRED, "Close a running application"),
            "open_website": ToolPermission("open_website", PermissionLevel.SAFE, "Open URL in browser"),
            "search_web": ToolPermission("search_web", PermissionLevel.SAFE, "Search Google"),
            "open_folder": ToolPermission("open_folder", PermissionLevel.SAFE, "Open folder in file explorer"),
            "open_file": ToolPermission("open_file", PermissionLevel.SAFE, "Open a file"),
            "get_system_info": ToolPermission("get_system_info", PermissionLevel.SAFE, "Read hardware and system specs"),
            "take_screenshot": ToolPermission("take_screenshot", PermissionLevel.SAFE, "Take screen snapshot"),
            "set_volume": ToolPermission("set_volume", PermissionLevel.SAFE, "Adjust system volume"),
            "play_pause_media": ToolPermission("play_pause_media", PermissionLevel.SAFE, "Toggle media playback"),
        }

    def get_permission(self, tool_name: str) -> Optional[ToolPermission]:
        """Get the permission profile for a tool."""
        return self._permissions.get(tool_name)

    def is_allowed(self, tool_name: str) -> bool:
        """Check if tool is known and not blocked."""
        perm = self.get_permission(tool_name)
        if not perm:
            return False
        return perm.level != PermissionLevel.BLOCKED

    def requires_confirmation(self, tool_name: str) -> bool:
        """Check if tool requires user confirmation prior to execution."""
        perm = self.get_permission(tool_name)
        if not perm:
            return True  # Unknown tools always require confirmation
        return perm.level in (PermissionLevel.CONFIRMATION_REQUIRED, PermissionLevel.HIGH_RISK)


# Global singleton
permission_manager = PermissionManager()
