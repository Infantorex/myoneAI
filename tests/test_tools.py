"""Comprehensive tests for Phase 8 Secure PC Assistant Tools.

Covers ToolRegistry, Schemas, ToolExecutor, PermissionManager, Policies,
Audit Logging, Intent Parsing, and ConversationManager Integration.
"""

import asyncio
import os
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.ai.manager import ConversationManager
from app.ai.provider import MockAIProvider
from app.core.config import Settings, get_settings
from app.security.audit import SecurityAuditLogger, audit_logger
from app.security.permissions import (
    PermissionLevel,
    PermissionManager,
    permission_manager,
)
from app.security.policies import (
    is_app_allowed,
    is_command_blocked,
    is_path_allowed,
    is_path_blocked,
    is_url_allowed,
    validate_safe_path,
)
from app.tools.applications import close_application, open_application
from app.tools.browser import open_website, search_web_browser
from app.tools.executor import ToolExecutor, tool_executor
from app.tools.filesystem import delete_file, list_directory, open_directory, open_file
from app.tools.intent import parse_tool_intent
from app.tools.media import (
    media_next,
    media_play_pause,
    media_previous,
    set_volume,
    toggle_mute,
    volume_down,
    volume_up,
)
from app.tools.registry import ToolRegistry, register_tool, tool_registry
from app.tools.schemas import (
    ToolCall,
    ToolNotFoundError,
    ToolPermissionDeniedError,
    ToolResult,
    ToolSchema,
    ToolTimeoutError,
    ToolValidationError,
)
from app.tools.screenshot import cleanup_old_screenshots, take_screenshot
from app.tools.system import (
    get_battery_status,
    get_cpu_usage,
    get_disk_usage,
    get_ram_usage,
    get_system_info,
)


# ==============================================================================
# 1. Tool Registry & Schemas Tests
# ==============================================================================

def test_tool_registry_registration_and_lookup():
    """Verify tool registration, schemas, and lookup."""
    reg = ToolRegistry()
    schema = ToolSchema(
        name="test_tool",
        description="A test tool",
        parameters={"arg1": "string"},
        required_params=["arg1"],
        permission=PermissionLevel.SAFE,
    )

    def dummy_handler(arg1: str):
        return f"Hello {arg1}"

    reg.register(schema, dummy_handler)
    assert reg.is_registered("test_tool")
    assert "test_tool" in reg.list_tool_names()

    entry = reg.get("test_tool")
    assert entry is not None
    s, h = entry
    assert s.name == "test_tool"
    assert h("World") == "Hello World"


def test_tool_registry_rejects_duplicates():
    """Verify registry raises error on duplicate tool name."""
    reg = ToolRegistry()
    schema = ToolSchema(name="duplicate_tool", description="Test")
    reg.register(schema, lambda: None)

    with pytest.raises(ValueError, match="already registered"):
        reg.register(schema, lambda: None)


def test_default_tool_registry_contains_expected_tools():
    """Verify global tool registry has standard PC tools."""
    names = tool_registry.list_tool_names()
    assert "open_application" in names
    assert "close_application" in names
    assert "open_website" in names
    assert "take_screenshot" in names
    assert "volume_up" in names
    assert "get_battery_status" in names
    assert "get_ram_usage" in names


# ==============================================================================
# 2. Security Policies & Path Validation Tests
# ==============================================================================

def test_url_allowed_schemes():
    """Verify allowed and forbidden URL schemes."""
    assert is_url_allowed("https://google.com")
    assert is_url_allowed("http://localhost:8000")
    assert is_url_allowed("www.youtube.com")

    # Forbidden schemes
    assert not is_url_allowed("file:///C:/Windows/System32/cmd.exe")
    assert not is_url_allowed("javascript:alert(1)")
    assert not is_url_allowed("data:text/html,<h1>hacked</h1>")
    assert not is_url_allowed("vbscript:MsgBox(1)")
    assert not is_url_allowed("")


def test_blocked_command_patterns():
    """Verify dangerous shell injection patterns are detected."""
    assert is_command_blocked("format C:")
    assert is_command_blocked("del /f /s /q *.*")
    assert is_command_blocked("powershell -Command Remove-Item")
    assert is_command_blocked("cmd.exe /c start")
    assert is_command_blocked("shutdown /r /t 0")
    assert not is_command_blocked("open chrome")
    assert not is_command_blocked("how is my battery")


def test_blocked_paths():
    """Verify system directories and credentials are blocked."""
    assert is_path_blocked("C:\\Windows\\System32\\calc.exe")
    assert is_path_blocked("C:\\Program Files\\app")
    assert is_path_blocked("C:\\Users\\dell\\.ssh\\id_rsa")
    assert is_path_blocked(".aws/credentials")
    assert not is_path_blocked("data\\screenshots\\test.png")


def test_app_allowlist_validation():
    """Verify safe application allowlist check."""
    allowed, target = is_app_allowed("chrome")
    assert allowed
    assert target is not None

    allowed, target = is_app_allowed("notepad")
    assert allowed

    allowed, target = is_app_allowed("calculator")
    assert allowed

    allowed, _ = is_app_allowed("arbitrary_malware.exe")
    assert not allowed


# ==============================================================================
# 3. Tool Executor & Permission Flow Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_tool_executor_safe_tool_execution():
    """Verify execution of a safe tool."""
    executor = ToolExecutor()
    call = ToolCall(tool="get_ram_usage", arguments={})
    result = await executor.execute(call)

    assert result.success
    assert result.tool == "get_ram_usage"
    assert "RAM" in result.message


@pytest.mark.asyncio
async def test_tool_executor_unknown_tool_rejected():
    """Verify unknown tool is safely rejected."""
    executor = ToolExecutor()
    call = ToolCall(tool="unregistered_tool_xyz", arguments={})
    result = await executor.execute(call)

    assert not result.success
    assert "not registered" in result.error or "Unknown tool" in result.message


@pytest.mark.asyncio
async def test_tool_executor_missing_parameter():
    """Verify missing required parameter triggers validation error."""
    executor = ToolExecutor()
    call = ToolCall(tool="open_application", arguments={})
    result = await executor.execute(call)

    assert not result.success
    assert "Missing parameter" in result.message or "Missing required parameter" in result.error


@pytest.mark.asyncio
async def test_tool_executor_blocked_action():
    """Verify blocked action returns blocked error."""
    executor = ToolExecutor()
    call = ToolCall(tool="open_application", arguments={"application": "unapproved_hacker_tool"})
    result = await executor.execute(call)

    assert not result.success
    assert "blocked" in result.message.lower() or "blocked" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_tool_executor_confirmation_required_flow():
    """Verify confirmation-required tool creates pending token and executes on confirm."""
    pm = PermissionManager()
    executor = ToolExecutor(permissions=pm)

    # 1. Initial attempt without confirmation -> requires_confirmation=True
    call = ToolCall(tool="close_application", arguments={"application": "notepad"})
    result = await executor.execute(call, confirmed=False)

    assert not result.success
    assert result.requires_confirmation
    assert result.confirmation_token is not None

    token = result.confirmation_token
    pending = pm.get_pending_confirmation(token)
    assert pending is not None
    assert pending.tool_name == "close_application"

    # 2. Mock close handler and execute with confirmed=True
    with patch("app.tools.applications.psutil.process_iter", return_value=[]):
        result2 = await executor.execute(call, confirmed=True)
        assert result2.success
        assert "Notepad" in result2.message


# ==============================================================================
# 4. Individual Tools Functionality Tests
# ==============================================================================

def test_open_application_safe():
    """Verify open_application invokes subprocess with allowlisted target."""
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = MagicMock()
        res = open_application("notepad")
        assert res.success
        assert "Notepad" in res.message


def test_open_website_url():
    """Verify open_website launches browser with safe URL."""
    with patch("webbrowser.open") as mock_open:
        res = open_website("https://google.com")
        assert res.success
        mock_open.assert_called_once()

    # Dangerous URL fails
    res_bad = open_website("file:///C:/Windows/cmd.exe")
    assert not res_bad.success


def test_search_web_browser():
    """Verify search_web_browser creates valid Google search query."""
    with patch("webbrowser.open") as mock_open:
        res = search_web_browser("Python programming tutorial")
        assert res.success
        mock_open.assert_called_once()
        assert "google.com/search" in mock_open.call_args[0][0]


def test_media_controls():
    """Verify media control functions return success."""
    with patch("ctypes.windll.user32.keybd_event"):
        r1 = volume_up(10)
        assert r1.success
        r2 = volume_down(10)
        assert r2.success
        r3 = toggle_mute()
        assert r3.success
        r4 = media_play_pause()
        assert r4.success
        r5 = media_next()
        assert r5.success
        r6 = media_previous()
        assert r6.success


def test_system_telemetry_tools():
    """Verify system telemetry tools return valid structured metrics."""
    r_bat = get_battery_status()
    assert r_bat.success

    r_cpu = get_cpu_usage()
    assert r_cpu.success
    assert "CPU" in r_cpu.message

    r_ram = get_ram_usage()
    assert r_ram.success
    assert "RAM" in r_ram.message

    r_disk = get_disk_usage()
    assert r_disk.success
    assert "Disk" in r_disk.message

    r_sys = get_system_info()
    assert r_sys.success
    assert "OS" in r_sys.message


def test_filesystem_tools_in_temp_dir():
    """Verify safe filesystem operations in an allowed temporary workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = get_settings()
        # Add tmpdir to allowed directories
        orig_allowed = settings.allowed_directories
        settings.allowed_directories = f"{orig_allowed},{tmpdir}"

        test_file = Path(tmpdir) / "phase8_sample.txt"
        test_file.write_text("myoneAI safe file test", encoding="utf-8")

        # 1. List directory
        list_res = list_directory(tmpdir)
        assert list_res.success
        assert "phase8_sample.txt" in list_res.message

        # 2. Open file
        with patch("os.startfile"):
            open_res = open_file(str(test_file))
            assert open_res.success

        # 3. Delete file
        del_res = delete_file(str(test_file))
        assert del_res.success
        assert not test_file.exists()

        # Restore
        settings.allowed_directories = orig_allowed


def test_screenshot_capture_and_cleanup():
    """Verify screenshot capture and retention cleanup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = get_settings()
        orig_dir = settings.screenshot_directory
        settings.screenshot_directory = tmpdir

        # Mock native screen capture to write dummy bitmap
        def mock_capture(path: Path):
            path.write_bytes(b"BM\x36\x00\x00\x00" + b"\x00" * 50)
            return 1920, 1080

        with patch("app.tools.screenshot._capture_screen_native", side_effect=mock_capture):
            res = take_screenshot()
            assert res.success
            assert "Screenshot" in res.message

        # Test cleanup
        old_file = Path(tmpdir) / "screenshot_20200101_000000.bmp"
        old_file.write_text("old")
        # Set mtime to 10 days ago
        old_time = time.time() - (10 * 86400)
        os.utime(old_file, (old_time, old_time))

        removed = cleanup_old_screenshots(directory=tmpdir, retention_days=7)
        assert removed >= 1
        assert not old_file.exists()

        settings.screenshot_directory = orig_dir



# ==============================================================================
# 5. Intent Parser Tests
# ==============================================================================

def test_parse_tool_intent_english():
    """Verify intent parser maps English commands to ToolCalls."""
    # Applications
    c1 = parse_tool_intent("Open Chrome")
    assert c1 is not None
    assert c1.tool == "open_application"
    assert c1.arguments["application"] == "chrome"

    c2 = parse_tool_intent("Close Notepad")
    assert c2 is not None
    assert c2.tool == "close_application"
    assert c2.arguments["application"] == "notepad"

    # Browser
    c3 = parse_tool_intent("Search Google for Python tutorial")
    assert c3 is not None
    assert c3.tool == "search_web_browser"
    assert "Python tutorial" in c3.arguments["query"]

    # Media & Screenshot
    c4 = parse_tool_intent("Volume up")
    assert c4 is not None
    assert c4.tool == "volume_up"

    c5 = parse_tool_intent("Take a screenshot")
    assert c5 is not None
    assert c5.tool == "take_screenshot"

    # System Info
    c6 = parse_tool_intent("How much RAM am I using?")
    assert c6 is not None
    assert c6.tool == "get_ram_usage"

    c7 = parse_tool_intent("Battery status")
    assert c7 is not None
    assert c7.tool == "get_battery_status"


def test_parse_tool_intent_tamil():
    """Verify intent parser maps Tamil and Tanglish commands."""
    # Tamil App Launch
    c1 = parse_tool_intent("Chrome open பண்ணு")
    assert c1 is not None
    assert c1.tool == "open_application"
    assert "chrome" in c1.arguments["application"].lower()

    # Tamil Volume
    c2 = parse_tool_intent("Volume குறை")
    assert c2 is not None
    assert c2.tool == "volume_down"

    # Tamil Screenshot
    c3 = parse_tool_intent("Screenshot எடு")
    assert c3 is not None
    assert c3.tool == "take_screenshot"

    # Tamil Battery
    c4 = parse_tool_intent("Battery எவ்வளவு இருக்கு?")
    assert c4 is not None
    assert c4.tool == "get_battery_status"

    # Tamil RAM
    c5 = parse_tool_intent("RAM usage என்ன?")
    assert c5 is not None
    assert c5.tool == "get_ram_usage"


def test_parse_tool_intent_blocked_command():
    """Verify blocked command syntax routes to blocked tool."""
    c = parse_tool_intent("format C:")
    assert c is not None
    assert c.tool == "execute_shell"


def test_parse_tool_intent_normal_query():
    """Verify normal conversation queries are NOT captured as tools."""
    c = parse_tool_intent("வானிலை எப்படி இருக்கிறது?")
    assert c is None

    c2 = parse_tool_intent("Tell me a story about robots")
    assert c2 is None


# ==============================================================================
# 6. ConversationManager Integration Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_conversation_manager_executes_tool_turn():
    """Verify ConversationManager parses and executes tool directly."""
    mock_prov = MockAIProvider()
    mgr = ConversationManager(provider=mock_prov)

    reply = await mgr.respond("How much RAM am I using?")
    assert "RAM" in reply
    assert mgr.history_length == 2
    assert mgr.get_history()[1].content == reply


@pytest.mark.asyncio
async def test_conversation_manager_confirmation_lifecycle():
    """Verify ConversationManager asks for confirmation and executes upon user 'Yes'."""
    pm = PermissionManager()
    mock_prov = MockAIProvider()
    mgr = ConversationManager(provider=mock_prov, permissions=pm)

    # 1. User asks to close app (requires confirmation)
    r1 = await mgr.respond("Close Notepad")
    assert "confirmation" in r1.lower() or "உறுதிப்படுத்துங்கள்" in r1

    pending = pm.get_pending_confirmation()
    assert pending is not None

    # 2. User confirms with 'Yes'
    with patch("app.tools.applications.psutil.process_iter", return_value=[]):
        r2 = await mgr.respond("Yes")
        assert "Notepad" in r2
        assert pm.get_pending_confirmation() is None


@pytest.mark.asyncio
async def test_conversation_manager_confirmation_cancellation():
    """Verify ConversationManager cancels action upon user 'No'."""
    pm = PermissionManager()
    mock_prov = MockAIProvider()
    mgr = ConversationManager(provider=mock_prov, permissions=pm)

    # 1. Ask dangerous action
    await mgr.respond("Close Notepad")
    assert pm.get_pending_confirmation() is not None

    # 2. User says 'Cancel'
    r2 = await mgr.respond("Cancel")
    assert "cancelled" in r2.lower() or "ரத்து" in r2
    assert pm.get_pending_confirmation() is None


# ==============================================================================
# 7. Security Audit Logging Tests
# ==============================================================================

def test_security_audit_logger():
    """Verify audit logger writes structured entries without leaking secrets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_file = Path(tmpdir) / "audit_test.log"
        logger = SecurityAuditLogger(log_file_path=audit_file)

        logger.log_tool_decision(
            tool_name="open_application",
            permission_level="SAFE",
            result="success",
            details="Opened chrome with key=sk-secretpassword123",
            duration_sec=0.05,
        )

        content = audit_file.read_text(encoding="utf-8")
        assert "tool=open_application" in content
        assert "permission=SAFE" in content
        assert "result=success" in content
        # Secrets must be sanitized
        assert "sk-secretpassword123" not in content
        assert "REDACTED" in content
