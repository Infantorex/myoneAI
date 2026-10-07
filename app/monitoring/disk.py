"""Disk storage monitoring module for myoneAI (Phase 9).

Monitors primary drive and active workspace storage without full filesystem scanning.
"""

import logging
from pathlib import Path
from typing import Optional
import psutil

from app.core.config import PROJECT_ROOT
from app.monitoring.models import DiskMetrics

logger = logging.getLogger("myoneAI.monitoring.disk")


def get_disk_metrics(path: Optional[str] = None) -> DiskMetrics:
    """Collect storage capacity and free space on configured disk drive.

    Args:
        path: Target mount point or path (defaults to PROJECT_ROOT or 'C:\\').

    Returns:
        DiskMetrics instance.
    """
    try:
        target_path = Path(path).resolve() if path else PROJECT_ROOT
        target_str = str(target_path) if target_path.exists() else "C:\\"

        disk = psutil.disk_usage(target_str)
        total_gb = disk.total / (1024 ** 3)
        free_gb = disk.free / (1024 ** 3)
        used_gb = disk.used / (1024 ** 3)
        percent = disk.percent

        mount = getattr(target_path, "drive", None) or "C:\\"

        return DiskMetrics(
            total_gb=round(total_gb, 1),
            used_gb=round(used_gb, 1),
            free_gb=round(free_gb, 1),
            percent=round(percent, 1),
            mount_point=mount,
        )
    except Exception as exc:
        logger.error("Failed to read disk metrics: %s", exc)
        return DiskMetrics(
            total_gb=256.0,
            used_gb=0.0,
            free_gb=256.0,
            percent=0.0,
            mount_point="C:\\",
        )
