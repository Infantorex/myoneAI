"""Process monitoring utilities.
"""

from typing import Any, Dict, List
import psutil


def get_top_processes(limit: int = 5) -> List[Dict[str, Any]]:
    """Return top resource consuming processes on-demand."""
    procs = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = proc.info
            procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Sort by memory percent descending
    procs.sort(key=lambda p: p.get("memory_percent") or 0.0, reverse=True)
    return procs[:limit]
