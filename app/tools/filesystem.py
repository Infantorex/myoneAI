"""Safe filesystem tools for myoneAI (Phase 8).

Provides allowlisted directory listing, folder navigation, file opening, and confirmed file deletion.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import PROJECT_ROOT
from app.security.policies import is_path_allowed, is_path_blocked
from app.tools.schemas import ToolResult

logger = logging.getLogger("myoneAI.tools.filesystem")


def list_directory(directory: Optional[str] = None) -> ToolResult:
    """List contents of an approved directory."""
    target = Path(directory).resolve() if directory else PROJECT_ROOT

    if not is_path_allowed(target):
        return ToolResult(
            success=False,
            tool="list_directory",
            message=f"Access to directory '{target}' is restricted.",
            error="Directory outside allowed boundaries.",
        )

    if not target.exists() or not target.is_dir():
        return ToolResult(
            success=False,
            tool="list_directory",
            message=f"Directory '{target}' does not exist.",
            error="Path not found or not a directory.",
        )

    try:
        entries = []
        for item in sorted(target.iterdir()):
            entries.append({
                "name": item.name,
                "is_dir": item.is_dir(),
                "size_bytes": item.stat().st_size if item.is_file() else 0,
            })

        names_summary = ", ".join(e["name"] for e in entries[:10])
        item_info = f": {names_summary}" if names_summary else ""
        return ToolResult(
            success=True,
            tool="list_directory",
            message=f"Found {len(entries)} items in {target.name or target}{item_info}.",
            data={"directory": str(target), "count": len(entries), "items": entries[:50]},
        )

    except Exception as exc:
        logger.error("Failed to list directory '%s': %s", target, exc)
        return ToolResult(
            success=False,
            tool="list_directory",
            message=f"Error listing directory: {exc}",
            error=str(exc),
        )


def open_directory(directory: Optional[str] = None) -> ToolResult:
    """Open an approved folder in the system file explorer."""
    target = Path(directory).resolve() if directory else PROJECT_ROOT

    if not is_path_allowed(target):
        return ToolResult(
            success=False,
            tool="open_directory",
            message=f"Access to directory '{target}' is restricted.",
            error="Directory outside allowed boundaries.",
        )

    if not target.exists() or not target.is_dir():
        return ToolResult(
            success=False,
            tool="open_directory",
            message=f"Directory '{target}' does not exist.",
            error="Directory not found.",
        )

    try:
        if os.name == "nt":
            os.startfile(str(target))
        else:
            import subprocess
            subprocess.Popen(["xdg-open", str(target)], shell=False)

        return ToolResult(
            success=True,
            tool="open_directory",
            message=f"Folder open பண்ணிட்டேன் ({target.name or target}).",
            data={"directory": str(target)},
        )
    except Exception as exc:
        logger.error("Failed to open directory in explorer '%s': %s", target, exc)
        return ToolResult(
            success=False,
            tool="open_directory",
            message=f"Failed to open folder: {exc}",
            error=str(exc),
        )


def open_file(file_path: str) -> ToolResult:
    """Open a file with its default system application."""
    target = Path(file_path).resolve()

    if is_path_blocked(target) or not is_path_allowed(target):
        return ToolResult(
            success=False,
            tool="open_file",
            message=f"Access to file '{target.name}' is restricted.",
            error="Path outside allowed boundaries.",
        )

    if not target.exists() or not target.is_file():
        return ToolResult(
            success=False,
            tool="open_file",
            message=f"File '{target.name}' not found.",
            error="File does not exist.",
        )

    try:
        if os.name == "nt":
            os.startfile(str(target))
        else:
            import subprocess
            subprocess.Popen(["xdg-open", str(target)], shell=False)

        return ToolResult(
            success=True,
            tool="open_file",
            message=f"File open பண்ணிட்டேன் ({target.name}).",
            data={"file": str(target)},
        )
    except Exception as exc:
        logger.error("Failed to open file '%s': %s", target, exc)
        return ToolResult(
            success=False,
            tool="open_file",
            message=f"Failed to open file: {exc}",
            error=str(exc),
        )


def delete_file(file_path: str) -> ToolResult:
    """Delete a file permanently within allowed user workspace."""
    target = Path(file_path).resolve()

    if is_path_blocked(target) or not is_path_allowed(target):
        return ToolResult(
            success=False,
            tool="delete_file",
            message=f"Cannot delete restricted or system path: '{target.name}'.",
            error="Deletion forbidden by security policy.",
        )

    if not target.exists() or not target.is_file():
        return ToolResult(
            success=False,
            tool="delete_file",
            message=f"File '{target.name}' does not exist.",
            error="File not found.",
        )

    try:
        target.unlink()
        logger.info("Deleted file: '%s'", target)
        return ToolResult(
            success=True,
            tool="delete_file",
            message=f"File '{target.name}' permanently deleted (நீக்கப்பட்டது).",
            data={"deleted_file": str(target)},
        )
    except Exception as exc:
        logger.error("Failed to delete file '%s': %s", target, exc)
        return ToolResult(
            success=False,
            tool="delete_file",
            message=f"Failed to delete file: {exc}",
            error=str(exc),
        )
