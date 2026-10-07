"""CPU monitoring module for myoneAI (Phase 9).

Provides on-demand CPU utilization, core topologies, and frequency without background busy-waiting.
"""

import logging
from typing import Optional
import psutil

from app.monitoring.models import CPUMetrics

logger = logging.getLogger("myoneAI.monitoring.cpu")


def get_cpu_metrics(sample_interval: Optional[float] = 0.1) -> CPUMetrics:
    """Collect current CPU utilization, logical core count, and frequency.

    Args:
        sample_interval: Duration in seconds to sample utilization (default 0.1s).

    Returns:
        CPUMetrics instance.
    """
    try:
        usage = psutil.cpu_percent(interval=sample_interval)
        logical_cores = psutil.cpu_count(logical=True) or 1
        physical_cores = psutil.cpu_count(logical=False)

        freq = None
        try:
            freq_info = psutil.cpu_freq()
            if freq_info:
                freq = round(freq_info.current, 1)
        except Exception:
            pass

        return CPUMetrics(
            usage_percent=round(usage, 1),
            logical_cores=logical_cores,
            physical_cores=physical_cores,
            frequency_mhz=freq,
        )
    except Exception as exc:
        logger.error("Failed to read CPU metrics: %s", exc)
        return CPUMetrics(
            usage_percent=0.0,
            logical_cores=1,
        )
