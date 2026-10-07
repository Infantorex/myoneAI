"""Network connectivity and latency monitor for myoneAI (Phase 9).

Performs lightweight socket-based connectivity checks without continuous ICMP pinging or packet sniffing.
"""

import logging
import socket
import time
from typing import Optional

from app.monitoring.models import NetworkMetrics

logger = logging.getLogger("myoneAI.monitoring.network")


def get_network_metrics(check_latency: bool = False, timeout_sec: float = 2.0) -> NetworkMetrics:
    """Collect basic network connection status and local host telemetry.

    Args:
        check_latency: Whether to perform an active round-trip connection test.
        timeout_sec: Timeout for socket connection check.

    Returns:
        NetworkMetrics instance.
    """
    hostname = socket.gethostname()
    ip_address = None
    is_connected = False
    latency_ms = None

    try:
        # Check local IP and general socket availability by connecting to a standard public DNS socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout_sec)
        try:
            # 8.8.8.8:53 doesn't actually send packets on connect for UDP, but resolves local outbound IP
            s.connect(("8.8.8.8", 53))
            ip_address = s.getsockname()[0]
            is_connected = True
        finally:
            s.close()
    except Exception:
        # Fallback to localhost resolution
        try:
            ip_address = socket.gethostbyname(hostname)
            is_connected = not ip_address.startswith("127.")
        except Exception:
            is_connected = False

    # Optional latency check if explicitly requested
    if is_connected and check_latency:
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout_sec)
            sock.connect(("1.1.1.1", 53))
            sock.close()
            latency_ms = round((time.time() - start) * 1000, 1)
        except Exception as exc:
            logger.debug("Latency check failed: %s", exc)
            latency_ms = None

    return NetworkMetrics(
        is_connected=is_connected,
        hostname=hostname,
        ip_address=ip_address,
        latency_ms=latency_ms,
    )
