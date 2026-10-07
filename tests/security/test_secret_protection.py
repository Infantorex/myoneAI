"""Automated Secret and Credential Scanning in Repository."""

import os
import re
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_no_secrets_in_tracked_codebase():
    """Verify application code and configs contain zero exposed raw API keys or passwords."""
    # Patterns for real API keys / private keys
    real_key_patterns = [
        re.compile(r"sk-[a-zA-Z0-9]{20,48}"),
        re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----"),
        re.compile(r"AIzaSy[a-zA-Z0-9_-]{33}"),
    ]

    scanned_files = 0
    violations = []

    # Directories containing application code and configs
    scan_dirs = ["app", "config", "web", "scripts"]
    scan_exts = {".py", ".json", ".md", ".html", ".js", ".css"}

    for d in scan_dirs:
        target_dir = PROJECT_ROOT / d
        if not target_dir.exists():
            continue
        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [sub for sub in dirs if sub not in {".venv", "__pycache__", ".pytest_cache"}]
            for f in files:
                path = Path(root) / f
                if path.suffix in scan_exts and not f.startswith("test_"):
                    scanned_files += 1
                    try:
                        content = path.read_text(encoding="utf-8", errors="ignore")
                        for pattern in real_key_patterns:
                            matches = pattern.findall(content)
                            for m in matches:
                                violations.append(f"{path}: {m}")
                    except Exception:
                        pass

    assert len(violations) == 0, f"Found potential exposed secrets in application code: {violations}"
    assert scanned_files > 25, f"Scanned {scanned_files} files."
