"""Process resource usage monitor for myoneAI (Phase 9).

Identifies top CPU and memory consuming processes on demand without continuous process table scanning.
"""

import logging
from typing import List, Optional
import psutil

from app.monitoring.models import ProcessItem, ProcessMetrics

logger = logging.getLogger("myoneAI.monitoring.processes")


def get_top_processes(limit: int = 5, sort_by: str = "memory") -> List[ProcessItem]:
    """Retrieve top resource-consuming processes.

    Args:
        limit: Number of top processes to return (default 5).
        sort_by: Metric to sort by ('memory' or 'cpu').

    Returns:
        List of ProcessItem dataclasses.
    """
    items: List[ProcessItem] = []
    total_count = 0

    try:
        for proc in psutil.process_iter(["pid", "name", "memory_percent", "memory_info", "cpu_percent"]):
            total_count += 1
            try:
                info = proc.info
                name = info.get("name") or "unknown"
                pid = info.get("pid") or 0
                mem_pct = info.get("memory_percent") or 0.0
                mem_info = info.get("memory_info")
                mem_mb = (mem_info.rss / (1024 * 1024)) if mem_info else 0.0
                cpu_pct = info.get("cpu_percent") or 0.0

                items.append(ProcessItem(
                    pid=pid,
                    name=name,
                    cpu_percent=round(cpu_pct, 1),
                    memory_percent=round(mem_pct, 1),
                    memory_mb=round(mem_mb, 1),
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if sort_by.lower() == "cpu":
            items.sort(key=lambda p: p.cpu_percent, reverse=True)
        else:
            items.sort(key=lambda p: p.memory_mb, reverse=True)

        return items[:limit]
    except Exception as exc:
        logger.error("Failed to query top processes: %s", exc)
        return []


def get_process_metrics(limit: int = 5) -> ProcessMetrics:
    """Collect overview of top memory and top CPU processes.

    Args:
        limit: Maximum number of processes per category.

    Returns:
        ProcessMetrics instance.
    """
    top_mem = get_top_processes(limit=limit, sort_by="memory")
    top_cpu = get_top_processes(limit=limit, sort_by="cpu")
    total_procs = len(psutil.pids()) if hasattr(psutil, "pids") else len(top_mem)

    return ProcessMetrics(
        top_memory=top_mem,
        top_cpu=top_cpu,
        total_processes=total_procs,
    )
