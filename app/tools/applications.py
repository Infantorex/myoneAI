"""Application management tools for myoneAI (Phase 8).

Handles launching and terminating allowlisted applications with strict safety boundaries.
"""

import logging
import os
import subprocess
import sys
from typing import Any, Dict
import psutil

from app.security.policies import is_app_allowed
from app.tools.schemas import ToolResult

logger = logging.getLogger("myoneAI.tools.applications")


def open_application(application: str) -> ToolResult:
    """Launch an allowlisted application by name or alias."""
    allowed, exe_name = is_app_allowed(application)
    if not allowed or not exe_name:
        return ToolResult(
            success=False,
            tool="open_application",
            message=f"'{application}' is not configured as an available application.",
            error="Application not allowlisted.",
        )

    logger.info("Opening approved application: '%s' (Executable: '%s')", application, exe_name)
    try:
        if sys.platform == "win32":
            try:
                # Use os.startfile for Windows native URI/app execution
                os.startfile(exe_name)
            except Exception:
                # Fallback to direct subprocess without shell
                subprocess.Popen([exe_name], shell=False)
        else:
            subprocess.Popen([exe_name], shell=False)

        return ToolResult(
            success=True,
            tool="open_application",
            message=f"{application.capitalize()} open பண்ணிட்டேன் (Opened {application.capitalize()}).",
            data={"application": application, "executable": exe_name},
        )
    except Exception as exc:
        logger.error("Failed to launch application '%s': %s", application, exc)
        return ToolResult(
            success=False,
            tool="open_application",
            message=f"Failed to open {application}: {exc}",
            error=str(exc),
        )


def close_application(application: str) -> ToolResult:
    """Terminate running processes matching an allowlisted application."""
    allowed, exe_name = is_app_allowed(application)
    if not allowed or not exe_name:
        return ToolResult(
            success=False,
            tool="close_application",
            message=f"'{application}' is not in the allowed application list.",
            error="Application not allowlisted.",
        )

    target_stem = exe_name.lower().replace(".exe", "")
    terminated_count = 0

    try:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                proc_name = proc.info.get("name", "").lower()
                if target_stem in proc_name:
                    proc.terminate()
                    terminated_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if terminated_count > 0:
            return ToolResult(
                success=True,
                tool="close_application",
                message=f"Closed {terminated_count} process(es) for {application.capitalize()}.",
                data={"application": application, "terminated_processes": terminated_count},
            )
        else:
            return ToolResult(
                success=True,
                tool="close_application",
                message=f"No running instances of {application.capitalize()} found.",
                data={"application": application, "terminated_processes": 0},
            )


    except Exception as exc:
        logger.error("Error terminating application '%s': %s", application, exc)
        return ToolResult(
            success=False,
            tool="close_application",
            message=f"Error closing {application}: {exc}",
            error=str(exc),
        )
