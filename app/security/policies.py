"""Centralized security policies for myoneAI — Tamil JARVIS (Phase 8).

Defines application allowlists, filesystem boundaries, URL scheme restrictions,
and forbidden system patterns to guarantee zero arbitrary code or shell execution.
"""

import logging
import os
from pathlib import Path
import re
from typing import Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse

from app.core.config import PROJECT_ROOT, get_settings

logger = logging.getLogger("myoneAI.security.policies")

# ------------------------------------------------------------------------------
# 1. Allowed Applications Mapping
# ------------------------------------------------------------------------------
DEFAULT_ALLOWED_APPLICATIONS: Dict[str, str] = {
    # Web Browsers
    "chrome": "chrome",
    "google chrome": "chrome",
    "google-chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "msedge": "msedge",
    "brave": "brave",
    "firefox": "firefox",

    # Productivity & Editors
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "vscode": "code",
    "vs code": "code",
    "code": "code",
    "visual studio code": "code",
    "wordpad": "write",

    # System Utilities
    "explorer": "explorer",
    "file explorer": "explorer",
    "files": "explorer",
    "task manager": "taskmgr",
    "taskmgr": "taskmgr",
    "paint": "mspaint",
    "mspaint": "mspaint",
}

# ------------------------------------------------------------------------------
# 2. URL Scheme Allowlist & Blocklist
# ------------------------------------------------------------------------------
ALLOWED_URL_SCHEMES: Set[str] = {"http", "https"}
FORBIDDEN_URL_SCHEMES: Set[str] = {"file", "javascript", "data", "vbscript", "blob", "about"}

# ------------------------------------------------------------------------------
# 3. Blocked System Paths (Windows Security Boundary)
# ------------------------------------------------------------------------------
FORBIDDEN_SYSTEM_PATHS: List[Path] = [
    Path(os.environ.get("SystemRoot", r"C:\Windows")),
    Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32",
    Path(os.environ.get("SystemRoot", r"C:\Windows")) / "SysWOW64",
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
    Path.home() / ".ssh",
    Path.home() / ".aws",
    Path.home() / "AppData" / "Local" / "Microsoft" / "Credentials",
]

# ------------------------------------------------------------------------------
# 4. Forbidden Shell & Destructive Command Keywords
# ------------------------------------------------------------------------------
FORBIDDEN_COMMAND_PATTERNS = [
    re.compile(r"(?i)\b(?:format|del|rmdir|reg\s+(?:add|delete)|cacls|icacls|net\s+user|powershell|cmd(?:\.exe)?|bash|wscript|cscript|shutdown|taskkill|curl|wget|certutil|bitsadmin)\b"),
    re.compile(r"(?i)\b(?:drop\s+table|mkfs|dd\s+if=|:\(\)\{ :\|:& \};:)\b"),
]


def get_allowed_applications() -> Dict[str, str]:
    """Retrieve full merged map of allowed applications from defaults and env overrides."""
    apps = dict(DEFAULT_ALLOWED_APPLICATIONS)
    settings = get_settings()
    if settings.allowed_applications:
        for entry in settings.allowed_applications.split(","):
            if "=" in entry:
                alias, executable = entry.split("=", 1)
                apps[alias.strip().lower()] = executable.strip()
            elif entry.strip():
                apps[entry.strip().lower()] = entry.strip()
    return apps


def is_app_allowed(app_name: str) -> Tuple[bool, Optional[str]]:
    """Validate whether an application name is in the safe allowlist.

    Args:
        app_name: Name or alias of the application requested.

    Returns:
        Tuple of (is_allowed: bool, executable_name: Optional[str])
    """
    clean_name = app_name.strip().lower()
    allowed_apps = get_allowed_applications()

    if clean_name in allowed_apps:
        return True, allowed_apps[clean_name]

    # Partial / substring match in aliases
    for alias, exe in allowed_apps.items():
        if alias == clean_name or alias in clean_name or clean_name in alias:
            return True, exe

    return False, None


def get_allowed_directories() -> List[Path]:
    """Return safe directories accessible by filesystem tools."""
    user_home = Path.home()
    allowed = [
        PROJECT_ROOT,
        user_home / "Documents",
        user_home / "Downloads",
        user_home / "Desktop",
        user_home / "Pictures",
        user_home / "Music",
        user_home / "Videos",
        PROJECT_ROOT / "data",
    ]

    settings = get_settings()
    if settings.allowed_directories:
        for custom_p in settings.allowed_directories.split(","):
            if custom_p.strip():
                p = Path(custom_p.strip()).resolve()
                if p.exists() and not is_path_blocked(p):
                    allowed.append(p)

    return allowed


def is_path_blocked(target_path: Union[str, Path]) -> bool:
    """Check if path targets sensitive system directories or credentials."""
    try:
        path_str = str(target_path).lower().replace("/", "\\")
        for sensitive in [".ssh", ".aws", "credentials", "id_rsa", "system32", "syswow64", "\\windows", "c:\\windows", "program files", "\\etc\\", "\\var\\", "\\root\\", "\\etc", "\\var"]:
            if sensitive in path_str:
                return True
        resolved = Path(target_path).resolve()
        for forbidden in FORBIDDEN_SYSTEM_PATHS:
            try:
                forbidden_resolved = forbidden.resolve()
                if resolved == forbidden_resolved or forbidden_resolved in resolved.parents:
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return True



def is_path_allowed(target_path: Union[str, Path]) -> bool:
    """Verify if a path resides within allowed directories and is not blocked."""
    if is_path_blocked(target_path):
        return False

    try:
        resolved = Path(target_path).resolve()
        for allowed in get_allowed_directories():
            try:
                allowed_resolved = allowed.resolve()
                if resolved == allowed_resolved or allowed_resolved in resolved.parents:
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False


def is_url_allowed(url: str) -> bool:
    """Validate that the URL uses only safe HTTP or HTTPS schemes."""
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url.strip())
        scheme = parsed.scheme.lower()
        if not scheme:
            # Assume https for standard domain inputs like 'youtube.com'
            return True
        return scheme in ALLOWED_URL_SCHEMES and scheme not in FORBIDDEN_URL_SCHEMES
    except Exception:
        return False


def is_command_blocked(command_str: str) -> bool:
    """Check whether a text string contains forbidden system commands."""
    if not command_str:
        return False

    for pattern in FORBIDDEN_COMMAND_PATTERNS:
        if pattern.search(command_str):
            return True
    return False


def validate_safe_path(target_path: Union[str, Path]) -> Path:
    """Validate and return resolved safe Path, or raise PermissionError if restricted."""
    if is_path_blocked(target_path):
        raise PermissionError(f"Access to system or sensitive path '{target_path}' is blocked.")
    if not is_path_allowed(target_path):
        raise PermissionError(f"Path '{target_path}' is outside allowed user directories.")
    return Path(target_path).resolve()

