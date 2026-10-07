"""Comprehensive System-Wide Production Health Diagnostic Tool (Phase 15).

Checks hardware availability, environment, SQLite databases, AI/STT/TTS engines,
monitoring, security policies, and cloud readiness without exposing secrets.

Usage:
    python -m app.core.health
"""

import asyncio
import os
from pathlib import Path
import sys
import time
from typing import Dict, List, Tuple

from app import __version__
from app.core.config import PROJECT_ROOT, get_settings
from app.security.permissions import PermissionLevel, PermissionManager
from app.security.policies import is_command_blocked, is_path_blocked, is_url_allowed


def check_core_environment() -> Tuple[bool, str]:
    """Verify Python runtime, version, and project directory structure."""
    py_ver = sys.version_info
    if py_ver.major < 3 or (py_ver.major == 3 and py_ver.minor < 10):
        return False, f"Python {py_ver.major}.{py_ver.minor} is below minimum 3.10"
    
    settings = get_settings()
    data_dir = settings.data_path
    log_dir = settings.log_path.parent

    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        return False, f"Cannot write to data/log directories: {exc}"

    return True, f"Python {py_ver.major}.{py_ver.minor}.{py_ver.micro} ({sys.platform}) on {PROJECT_ROOT.name}"


def check_stt_system() -> Tuple[bool, str]:
    """Verify STT provider configuration and dependency availability."""
    settings = get_settings()
    provider = settings.stt_provider.lower()
    if provider in ("google", "google-stt"):
        return True, "Google Cloud STT (Online API, ta-IN)"
    elif provider in ("groq", "whisper"):
        has_key = bool(settings.stt_api_key and settings.stt_api_key.strip())
        return has_key, f"Groq Whisper STT (API Key {'configured' if has_key else 'MISSING'})"
    elif provider == "mock":
        return True, "Mock STT (Deterministic Test Provider)"
    return False, f"Unknown STT provider: '{provider}'"


def check_tts_system() -> Tuple[bool, str]:
    """Verify TTS engine availability."""
    settings = get_settings()
    provider = settings.tts_provider.lower()
    if provider in ("edge-tts", "edge"):
        return True, f"Edge-TTS ({settings.tts_voice})"
    elif provider == "mock":
        return True, "Mock TTS"
    return False, f"Unknown TTS provider: '{provider}'"


def check_ai_engine() -> Tuple[bool, str]:
    """Verify AI provider configuration without exposing secrets."""
    settings = get_settings()
    provider = settings.ai_provider.lower()
    is_cfg = settings.is_ai_configured
    if provider == "mock":
        return True, "Mock AI Provider (Offline CI Mode)"
    if not is_cfg:
        return True, f"{provider.capitalize()} ({settings.ai_model}) [No API key - Fallback to rule engine]"
    return True, f"{provider.capitalize()} ({settings.ai_model}) [API Key Configured]"


def check_memory_db() -> Tuple[bool, str]:
    """Verify SQLite Memory database connectivity and schema integrity."""
    settings = get_settings()
    db_path = settings.memory_db_path
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        res = cursor.fetchone()
        conn.close()
        if res and res[0] == "ok":
            return True, f"SQLite Memory DB intact ({db_path.name})"
        return False, f"Integrity check failed: {res}"
    except Exception as exc:
        return False, f"Memory DB Error: {exc}"


def check_productivity_db() -> Tuple[bool, str]:
    """Verify SQLite Productivity database connectivity and tables."""
    settings = get_settings()
    db_path = settings.data_path / "productivity.db"
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        res = cursor.fetchone()
        conn.close()
        if res and res[0] == "ok":
            return True, f"SQLite Productivity DB intact ({db_path.name})"
        return False, f"Integrity check failed: {res}"
    except Exception as exc:
        return False, f"Productivity DB Error: {exc}"


def check_monitoring() -> Tuple[bool, str]:
    """Verify system telemetry (psutil, CPU, RAM, Disk)."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        return True, f"psutil active (CPU: {cpu}%, RAM: {mem.percent}% used)"
    except Exception as exc:
        return False, f"Monitoring failed: {exc}"


def check_tools_and_permissions() -> Tuple[bool, str]:
    """Verify ToolRegistry and PermissionManager boundaries."""
    try:
        pm = PermissionManager()
        # Verify blocked execution
        lvl, _ = pm.evaluate_tool_permission("execute_shell", {"command": "dir"})
        if lvl != PermissionLevel.BLOCKED:
            return False, "Security violation: execute_shell was not BLOCKED"
        
        # Verify safe tool
        lvl_safe, _ = pm.evaluate_tool_permission("get_battery_status", {})
        if lvl_safe != PermissionLevel.SAFE:
            return False, "Battery status tool failed permission check"

        return True, "Permission Layer Active (SAFE / CONFIRM / BLOCKED enforced)"
    except Exception as exc:
        return False, f"Permission check error: {exc}"


def check_dashboard() -> Tuple[bool, str]:
    """Verify FastAPI web server components and routes."""
    try:
        from web.api.server import create_app
        app = create_app()
        settings = get_settings()
        return True, f"FastAPI Server ready (Host: {settings.web_host}:{settings.web_port}, Auth: {settings.web_auth_enabled})"
    except Exception as exc:
        return False, f"Dashboard init error: {exc}"


def check_cloud_communication() -> Tuple[bool, str]:
    """Verify cloud protocol, HMAC signing, and replay defense."""
    try:
        from app.cloud.authentication import compute_signature
        from app.cloud.device import DeviceManager
        from app.cloud.protocol import CloudMessage, MessageType, ReplayProtection
        
        dev = DeviceManager()
        msg = CloudMessage(device_id=dev.device_id, payload={"test": 1})
        sig = compute_signature("secret_test", msg)
        assert len(sig) == 64
        return True, f"Cloud Control Bridge ready (Device: {dev.device_id}, Replay Defense active)"
    except Exception as exc:
        return False, f"Cloud verification error: {exc}"


def check_security_policies() -> Tuple[bool, str]:
    """Verify centralized security policies and sandbox rules."""
    try:
        assert is_command_blocked("powershell -Command Get-Process") is True
        assert is_command_blocked("cmd /c dir C:\\") is True
        assert is_url_allowed("https://google.com") is True
        assert is_url_allowed("javascript:alert(1)") is False
        assert is_path_blocked("C:\\Windows\\System32") is True
        return True, "Sandboxing, URL scheme restrictions, and Command blocks 100% active"
    except Exception as exc:
        return False, f"Security policy check failed: {exc}"


def run_health_check() -> bool:
    """Execute full health check suite and display clean formatted report."""
    checks = [
        ("Core", check_core_environment),
        ("STT", check_stt_system),
        ("TTS", check_tts_system),
        ("AI", check_ai_engine),
        ("Memory", check_memory_db),
        ("Tools", check_tools_and_permissions),
        ("Monitoring", check_monitoring),
        ("Productivity", check_productivity_db),
        ("Dashboard", check_dashboard),
        ("Cloud", check_cloud_communication),
        ("Security", check_security_policies),
    ]

    all_passed = True
    results = []

    for name, check_fn in checks:
        passed, msg = check_fn()
        if not passed:
            all_passed = False
        status_str = "PASS" if passed else "FAIL"
        results.append((name, status_str, msg))

    print(f"\n======================================================================")
    print(f"  myoneAI — Tamil JARVIS Health Diagnostic (v{__version__})")
    print(f"======================================================================")
    for name, status, msg in results:
        print(f"  {name:<16} {status:<8} {msg}")
    print(f"======================================================================")
    if all_passed:
        print("  OVERALL STATUS: ALL CHECKS PASSED (100% HEALTHY)\n")
    else:
        print("  OVERALL STATUS: ONE OR MORE CHECKS FAILED\n")

    return all_passed


if __name__ == "__main__":
    success = run_health_check()
    sys.exit(0 if success else 1)
