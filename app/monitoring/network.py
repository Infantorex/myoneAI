"""Network status collector.
"""

from typing import Any, Dict
import psutil


def get_network_status() -> Dict[str, Any]:
    """Fetch network input/output counters."""
    io = psutil.net_io_counters()
    return {
        "bytes_sent_mb": round(io.bytes_sent / (1024 * 1024), 2),
        "bytes_recv_mb": round(io.bytes_recv / (1024 * 1024), 2),
        "packets_sent": io.packets_sent,
        "packets_recv": io.packets_recv,
    }
