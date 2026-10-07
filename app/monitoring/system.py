"""System hardware metrics collector (CPU, RAM, Disk).
"""

from typing import Any, Dict
import psutil


def get_system_summary() -> Dict[str, Any]:
    """Collect instantaneous system metrics on-demand without background polling."""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/") if hasattr(psutil, "disk_usage") else None
    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "ram_percent": mem.percent,
        "ram_used_gb": round((mem.total - mem.available) / (1024 ** 3), 2),
        "ram_total_gb": round(mem.total / (1024 ** 3), 2),
        "disk_percent": disk.percent if disk else None,
        "disk_free_gb": round(disk.free / (1024 ** 3), 2) if disk else None,
    }
