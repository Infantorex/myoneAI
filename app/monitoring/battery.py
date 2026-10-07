"""Battery and power state monitor for myoneAI (Phase 9).

Gracefully detects battery percentage, AC adapter connection, and charging status.
"""

import logging
from typing import Optional
import psutil

from app.monitoring.models import BatteryMetrics

logger = logging.getLogger("myoneAI.monitoring.battery")


def get_battery_metrics() -> BatteryMetrics:
    """Collect laptop battery telemetry.

    Returns:
        BatteryMetrics with is_available=True if battery exists, or is_available=False on desktop/no battery.
    """
    try:
        sensors_battery = getattr(psutil, "sensors_battery", None)
        if not sensors_battery:
            return BatteryMetrics(
                percent=100.0,
                power_plugged=True,
                is_available=False,
            )

        batt = sensors_battery()
        if not batt:
            return BatteryMetrics(
                percent=100.0,
                power_plugged=True,
                is_available=False,
            )

        is_charging = bool(batt.power_plugged and batt.percent < 100)
        secsleft = batt.secsleft if (batt.secsleft and batt.secsleft != psutil.POWER_TIME_UNLIMITED) else None

        return BatteryMetrics(
            percent=round(batt.percent, 1),
            power_plugged=bool(batt.power_plugged),
            secsleft=secsleft,
            is_charging=is_charging,
            is_available=True,
        )
    except Exception as exc:
        logger.debug("Failed to read battery metrics: %s", exc)
        return BatteryMetrics(
            percent=100.0,
            power_plugged=True,
            is_available=False,
        )
