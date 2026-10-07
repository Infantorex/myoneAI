"""System telemetry and hardware information tools for myoneAI (Phase 8).

Safe, read-only diagnostic metrics using psutil and platform.
"""

import logging
import platform
from pathlib import Path
import psutil
from typing import Any, Dict

from app.core.config import PROJECT_ROOT
from app.tools.schemas import ToolResult

logger = logging.getLogger("myoneAI.tools.system")



def get_system_info() -> ToolResult:
    """Retrieve general hardware, OS, and runtime specifications."""
    try:
        cpu_pct = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        battery_info = "N/A"
        sensors_battery = getattr(psutil, "sensors_battery", None)
        if sensors_battery:
            batt = sensors_battery()
            if batt:
                plugged_str = "charging" if batt.power_plugged else "on battery"
                battery_info = f"{batt.percent:.0f}% ({plugged_str})"

        os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
        ram_used_gb = (mem.total - mem.available) / (1024 ** 3)
        ram_total_gb = mem.total / (1024 ** 3)

        msg = (
            f"OS: {os_info} | CPU: {cpu_pct:.1f}% | "
            f"RAM: {ram_used_gb:.1f}GB / {ram_total_gb:.1f}GB ({mem.percent:.0f}%) | "
            f"Battery: {battery_info}"
        )

        return ToolResult(
            success=True,
            tool="get_system_info",
            message=msg,
            data={
                "os": os_info,
                "hostname": platform.node(),
                "cpu_percent": cpu_pct,
                "ram_percent": mem.percent,
                "ram_used_gb": round(ram_used_gb, 2),
                "ram_total_gb": round(ram_total_gb, 2),
                "disk_percent": disk.percent,
                "battery": battery_info,
            },
        )
    except Exception as exc:
        logger.error("Failed to fetch system info: %s", exc)
        return ToolResult(
            success=False,
            tool="get_system_info",
            message=f"Error reading system info: {exc}",
            error=str(exc),
        )


def get_battery_status() -> ToolResult:
    """Fetch current battery charge percentage and power connection state."""
    try:
        sensors_battery = getattr(psutil, "sensors_battery", None)
        if not sensors_battery:
            return ToolResult(
                success=True,
                tool="get_battery_status",
                message="Battery status is not supported on this platform.",
                data={"supported": False},
            )

        batt = sensors_battery()
        if not batt:
            return ToolResult(
                success=True,
                tool="get_battery_status",
                message="No battery detected (Desktop / AC powered).",
                data={"battery_present": False},
            )

        state_str = "charging" if batt.power_plugged else "on battery power"
        tamil_msg = f"Battery {batt.percent:.0f}% உள்ளது ({'சார்ஜிங் ஆகிறது' if batt.power_plugged else 'பேட்டரியில் இயங்குகிறது'})."

        return ToolResult(
            success=True,
            tool="get_battery_status",
            message=tamil_msg,
            data={
                "percent": batt.percent,
                "power_plugged": batt.power_plugged,
                "secsleft": batt.secsleft if batt.secsleft != psutil.POWER_TIME_UNLIMITED else None,
            },
        )
    except Exception as exc:
        logger.error("Failed to query battery status: %s", exc)
        return ToolResult(
            success=False,
            tool="get_battery_status",
            message=f"Error querying battery: {exc}",
            error=str(exc),
        )


def get_cpu_usage() -> ToolResult:
    """Read active CPU load percentage."""
    try:
        cpu_pct = psutil.cpu_percent(interval=0.2)
        cores = psutil.cpu_count(logical=True)
        return ToolResult(
            success=True,
            tool="get_cpu_usage",
            message=f"CPU பயன்பாடு (CPU usage): {cpu_pct:.1f}% ({cores} logical cores).",
            data={"cpu_percent": cpu_pct, "cores": cores},
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="get_cpu_usage",
            message=f"Failed to read CPU usage: {exc}",
            error=str(exc),
        )


def get_ram_usage() -> ToolResult:
    """Read memory utilization and free capacity."""
    try:
        mem = psutil.virtual_memory()
        used_mb = (mem.total - mem.available) / (1024 * 1024)
        total_mb = mem.total / (1024 * 1024)
        return ToolResult(
            success=True,
            tool="get_ram_usage",
            message=f"RAM பயன்பாடு: {used_mb:.0f}MB / {total_mb:.0f}MB ({mem.percent:.0f}%).",
            data={
                "ram_percent": mem.percent,
                "used_mb": round(used_mb, 1),
                "total_mb": round(total_mb, 1),
                "available_mb": round(mem.available / (1024 * 1024), 1),
            },
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="get_ram_usage",
            message=f"Failed to read RAM usage: {exc}",
            error=str(exc),
        )


def get_disk_usage() -> ToolResult:
    """Read storage disk capacity and available space."""
    try:
        target_path = str(PROJECT_ROOT) if PROJECT_ROOT.exists() else "C:\\"
        disk = psutil.disk_usage(target_path)
        total_gb = disk.total / (1024 ** 3)
        free_gb = disk.free / (1024 ** 3)
        return ToolResult(
            success=True,
            tool="get_disk_usage",
            message=f"Disk பயன்பாடு: {disk.percent:.0f}% (Free: {free_gb:.1f}GB / {total_gb:.1f}GB).",
            data={"disk_percent": disk.percent, "free_gb": round(free_gb, 1), "total_gb": round(total_gb, 1)},
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="get_disk_usage",
            message=f"Failed to read disk usage: {exc}",
            error=str(exc),
        )

