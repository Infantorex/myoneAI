"""Battery status telemetry collector.
"""

from typing import Any, Dict, Optional
import psutil


def get_battery_status() -> Optional[Dict[str, Any]]:
    """Fetch current battery level and charging state if available."""
    sensors_battery = getattr(psutil, "sensors_battery", None)
    if not sensors_battery:
        return None

    battery = sensors_battery()
    if not battery:
        return None

    return {
        "percent": round(battery.percent, 1),
        "power_plugged": battery.power_plugged,
        "secsleft": battery.secsleft,
    }
