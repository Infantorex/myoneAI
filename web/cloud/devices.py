"""Cloud Device Registry and Session Store for Vercel Control Plane (Phase 12).

Tracks connected laptop devices, telemetry snapshots, and pending cloud command requests in memory.
"""

from datetime import datetime
import logging
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("myoneAI.cloud.registry")


class CloudDeviceRegistry:
    """Thread-safe store for registered laptop devices on the Cloud Control Plane."""

    def __init__(self, offline_timeout_seconds: float = 90.0) -> None:
        self.offline_timeout_seconds = offline_timeout_seconds
        self._devices: Dict[str, Dict[str, Any]] = {}
        self._pending_commands: Dict[str, List[Dict[str, Any]]] = {}
        self._command_responses: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def register_device(self, device_id: str, info: Dict[str, Any]) -> Dict[str, Any]:
        """Register or update a laptop device profile."""
        now = time.time()
        record = {
            "device_id": device_id,
            "device_name": info.get("device_name", "MyOneAI-Laptop"),
            "device_version": info.get("device_version", "1.0.0"),
            "platform_os": info.get("platform_os", "Windows"),
            "registered_at": info.get("registered_at", datetime.now().isoformat()),
            "last_seen": now,
            "telemetry": {},
            "status": "online",
        }
        with self._lock:
            self._devices[device_id] = record
            if device_id not in self._pending_commands:
                self._pending_commands[device_id] = []
        logger.info("Cloud registered device: %s (%s)", device_id, record["device_name"])
        return record

    def record_heartbeat(self, device_id: str, telemetry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Record live heartbeat metrics from a laptop."""
        now = time.time()
        with self._lock:
            if device_id not in self._devices:
                self.register_device(device_id, telemetry)
            
            dev = self._devices[device_id]
            dev["last_seen"] = now
            dev["telemetry"] = telemetry
            dev["status"] = "online"
            return dev

    def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve live status and telemetry for a specific device."""
        now = time.time()
        with self._lock:
            dev = self._devices.get(device_id)
            if not dev:
                return None
            
            # Determine online/offline status based on timeout
            is_active = (now - dev["last_seen"]) <= self.offline_timeout_seconds
            status_str = "online" if is_active else "offline"
            dev_copy = dict(dev)
            dev_copy["status"] = status_str
            dev_copy["last_seen_iso"] = datetime.fromtimestamp(dev["last_seen"]).isoformat()
            return dev_copy

    def list_devices(self) -> List[Dict[str, Any]]:
        """List all known registered devices."""
        with self._lock:
            return [self.get_device_status(d_id) for d_id in self._devices.keys() if self.get_device_status(d_id) is not None]

    def queue_command(self, device_id: str, command_dict: Dict[str, Any]) -> None:
        """Enqueue a command for a laptop to execute."""
        with self._lock:
            if device_id not in self._pending_commands:
                self._pending_commands[device_id] = []
            self._pending_commands[device_id].append(command_dict)

    def get_pending_commands(self, device_id: str) -> List[Dict[str, Any]]:
        """Retrieve and drain all pending commands for a device."""
        with self._lock:
            cmds = self._pending_commands.get(device_id, [])
            self._pending_commands[device_id] = []
            return cmds

    def record_response(self, command_id: str, response_dict: Dict[str, Any]) -> None:
        """Record execution outcome received from laptop."""
        with self._lock:
            self._command_responses[command_id] = response_dict

    def get_response(self, command_id: str) -> Optional[Dict[str, Any]]:
        """Fetch result for a previously queued command."""
        with self._lock:
            return self._command_responses.get(command_id)

    def disconnect_device(self, device_id: str) -> bool:
        """Mark device as explicitly disconnected."""
        with self._lock:
            if device_id in self._devices:
                self._devices[device_id]["status"] = "offline"
                return True
            return False

    def clear(self) -> None:
        """Reset registry (for testing)."""
        with self._lock:
            self._devices.clear()
            self._pending_commands.clear()
            self._command_responses.clear()


# Global cloud device registry singleton
cloud_device_registry = CloudDeviceRegistry()
