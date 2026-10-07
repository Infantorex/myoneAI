"""RAM / Memory monitoring module for myoneAI (Phase 9).

Provides on-demand physical memory utilization metrics.
"""

import logging
import psutil

from app.monitoring.models import MemoryMetrics

logger = logging.getLogger("myoneAI.monitoring.memory")


def get_memory_metrics() -> MemoryMetrics:
    """Collect current system memory utilization and capacities.

    Returns:
        MemoryMetrics instance.
    """
    try:
        mem = psutil.virtual_memory()
        total_mb = mem.total / (1024 * 1024)
        available_mb = mem.available / (1024 * 1024)
        used_mb = (mem.total - mem.available) / (1024 * 1024)
        percent = mem.percent

        return MemoryMetrics(
            total_mb=round(total_mb, 1),
            used_mb=round(used_mb, 1),
            available_mb=round(available_mb, 1),
            percent=round(percent, 1),
        )
    except Exception as exc:
        logger.error("Failed to read memory metrics: %s", exc)
        return MemoryMetrics(
            total_mb=8192.0,
            used_mb=0.0,
            available_mb=8192.0,
            percent=0.0,
        )
