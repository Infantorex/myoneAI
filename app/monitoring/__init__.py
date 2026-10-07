"""Monitoring module for myoneAI.

Provides event-based, on-demand hardware and OS health telemetry.
Zero continuous polling overhead when idle.
"""

from app.monitoring.system import get_system_summary
from app.monitoring.battery import get_battery_status
from app.monitoring.network import get_network_status
from app.monitoring.process import get_top_processes

__all__ = [
    "get_system_summary",
    "get_battery_status",
    "get_network_status",
    "get_top_processes",
]
