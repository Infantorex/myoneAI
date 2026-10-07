"""Unit tests for permission manager and tool safety categorization (app/security/permissions.py).
"""

from app.security.permissions import PermissionManager, PermissionLevel


def test_permission_levels():
    """Verify tool permissions classifications."""
    pm = PermissionManager()

    # Safe tools
    assert pm.is_allowed("open_application")
    assert not pm.requires_confirmation("open_application")
    assert pm.get_permission("open_application").level == PermissionLevel.SAFE

    # Confirmation required tools
    assert pm.is_allowed("close_application")
    assert pm.requires_confirmation("close_application")
    assert pm.get_permission("close_application").level == PermissionLevel.CONFIRMATION_REQUIRED

    # Unknown tools
    assert not pm.is_allowed("unknown_destructive_action")
    assert pm.requires_confirmation("unknown_destructive_action")
