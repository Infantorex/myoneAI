"""Security and permissions subsystem for myoneAI — Tamil JARVIS (Phase 8)."""

from app.security.audit import SecurityAuditLogger, audit_logger
from app.security.permissions import (
    PendingConfirmation,
    PermissionLevel,
    PermissionManager,
    permission_manager,
)
from app.security.policies import (
    DEFAULT_ALLOWED_APPLICATIONS,
    FORBIDDEN_COMMAND_PATTERNS,
    FORBIDDEN_SYSTEM_PATHS,
    get_allowed_applications,
    get_allowed_directories,
    is_app_allowed,
    is_command_blocked,
    is_path_allowed,
    is_path_blocked,
    is_url_allowed,
)

__all__ = [
    "PermissionLevel",
    "PermissionManager",
    "permission_manager",
    "PendingConfirmation",
    "SecurityAuditLogger",
    "audit_logger",
    "get_allowed_applications",
    "get_allowed_directories",
    "is_app_allowed",
    "is_path_allowed",
    "is_path_blocked",
    "is_url_allowed",
    "is_command_blocked",
    "DEFAULT_ALLOWED_APPLICATIONS",
    "FORBIDDEN_SYSTEM_PATHS",
    "FORBIDDEN_COMMAND_PATTERNS",
]
