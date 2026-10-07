"""Lightweight periodic heartbeat generator for Cloud Communication (Phase 12).

Constructs sanitized system health telemetry snapshots for transmission to the cloud control plane.
"""

from datetime import datetime
import logging
from typing import Any, Dict, Optional

from app.cloud.authentication import sign_message
from app.cloud.device import DeviceManager, device_manager
from app.cloud.protocol import CloudMessage, MessageType
from app.core.config import Settings, get_settings
from app.core.state import state_manager
from app.monitoring.manager import MonitoringManager, monitoring_manager

logger = logging.getLogger("myoneAI.cloud.heartbeat")


class HeartbeatManager:
    """Builds and manages periodic cloud heartbeat payloads."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        device: Optional[DeviceManager] = None,
        monitoring: Optional[MonitoringManager] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.device = device or (DeviceManager(settings=self.settings) if settings else device_manager)
        self.monitoring = monitoring or monitoring_manager

    async def build_heartbeat_message(self) -> CloudMessage:
        """Collect live hardware telemetry and format a signed CloudMessage."""
        snapshot = await self.monitoring.get_snapshot(include_processes=False, sample_interval=0.05)
        raw_state = state_manager.current_state.value

        battery_pct = snapshot.battery.percent if snapshot.battery and snapshot.battery.is_available else None
        battery_plugged = snapshot.battery.power_plugged if snapshot.battery and snapshot.battery.is_available else None

        payload: Dict[str, Any] = {
            "status": "online",
            "assistant_state": raw_state,
            "cpu_percent": round(snapshot.cpu.usage_percent, 1),
            "memory_percent": round(snapshot.memory.percent, 1),
            "disk_percent": round(snapshot.disk.percent, 1),
            "battery_percent": round(battery_pct, 1) if battery_pct is not None else None,
            "battery_plugged": battery_plugged,
            "uptime_seconds": round(state_manager.uptime_seconds, 1),
            "version": getattr(self.settings, "app_version", "1.0.0"),
            "device_name": self.device.identity.device_name,
            "timestamp_iso": datetime.now().isoformat(),
        }

        msg = CloudMessage(
            type=MessageType.HEARTBEAT.value,
            device_id=self.device.device_id,
            payload=payload,
        )

        secret = self.settings.cloud_auth_token.strip() if self.settings.cloud_auth_token else ""
        if secret:
            sign_message(secret, msg)

        return msg


# Global heartbeat manager singleton
heartbeat_manager = HeartbeatManager()
