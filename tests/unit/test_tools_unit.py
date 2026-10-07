"""Unit tests for Phase 8 Secure PC Assistant Tools & Permissions."""

import asyncio
import pytest

from app.security.permissions import PermissionLevel, PermissionManager
from app.tools.executor import ToolExecutor
from app.tools.intent import parse_tool_intent
from app.tools.registry import ToolRegistry
from app.tools.schemas import ToolCall


def test_permission_level_tiers():
    """Verify default permission levels categorize SAFE, CONFIRM, and BLOCKED tools."""
    pm = PermissionManager()

    # Safe tools
    lvl, _ = pm.evaluate_tool_permission("open_website", {"url": "https://google.com"})
    assert lvl == PermissionLevel.SAFE

    # Blocked tools
    lvl, _ = pm.evaluate_tool_permission("execute_shell", {"command": "dir"})
    assert lvl == PermissionLevel.BLOCKED

    # Confirmation-required tools
    lvl, _ = pm.evaluate_tool_permission("delete_file", {"path": "test.txt"})
    assert lvl == PermissionLevel.CONFIRMATION_REQUIRED


def test_intent_parsing_english_and_tamil():
    """Verify tool intent parser extracts structured ToolCall from natural speech."""
    # 1. English
    call = parse_tool_intent("open chrome")
    assert call is not None
    assert call.tool == "open_application"
    assert call.arguments["application"].lower() == "chrome"

    # 2. Tamil
    call_ta = parse_tool_intent("youtube open பண்ணு")
    assert call_ta is not None
    assert call_ta.tool in ("open_application", "open_website")


@pytest.mark.asyncio
async def test_tool_executor_safe_execution():
    """Verify ToolExecutor safely executes allowlisted tools."""
    pm = PermissionManager()
    executor = ToolExecutor(permissions=pm)

    call = ToolCall(tool="get_battery_status", arguments={})
    res = await executor.execute(call)
    assert res.success is True
    assert "battery" in str(res.data) or "percent" in str(res.data)
