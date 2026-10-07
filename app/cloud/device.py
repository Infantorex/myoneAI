"""Device identity and registration management for Cloud Communication (Phase 12).

Maintains persistent, non-hardware-dependent device identity without leaking MAC addresses or passwords.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
import logging
from pathlib import Path
import platform
import time
from typing import Any, Dict, Optional
import uuid

from app.core.config import Settings, get_settings

logger = logging.getLogger("myoneAI.cloud.device")


@dataclass
class DeviceIdentity:
    """Encapsulates registered laptop identity profile."""
    device_id: str
    device_name: str
    device_version: str
    platform_os: str
    registered_at: str
    last_seen: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceIdentity":
        return cls(
            device_id=data["device_id"],
            device_name=data.get("device_name", "MyOneAI-Laptop"),
            device_version=data.get("device_version", "1.0.0"),
            platform_os=data.get("platform_os", "Windows"),
            registered_at=data.get("registered_at", datetime.now().isoformat()),
            last_seen=float(data.get("last_seen", time.time())),
        )


class DeviceManager:
    """Manages persistent device registration and identity profile."""

    def __init__(self, settings: Optional[Settings] = None, storage_path: Optional[Path] = None) -> None:
        self.settings = settings or get_settings()
        self.storage_path = storage_path or (self.settings.data_path / "device.json")
        self._identity: Optional[DeviceIdentity] = None
        self._load_or_init()

    @property
    def identity(self) -> DeviceIdentity:
        """Get the active device identity."""
        if not self._identity:
            self._load_or_init()
        return self._identity

    @property
    def device_id(self) -> str:
        """Return canonical device ID."""
        return self.identity.device_id

    def _load_or_init(self) -> None:
        """Load persistent device profile from disk or initialize a new one."""
        # 1. If configured explicitly in settings / env
        cfg_id = self.settings.cloud_device_id.strip() if self.settings.cloud_device_id else ""
        cfg_name = self.settings.cloud_device_name.strip() if self.settings.cloud_device_name else "MyOneAI-Laptop"
        app_ver = getattr(self.settings, "app_version", "1.0.0")

        # 2. Check local disk storage
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._identity = DeviceIdentity.from_dict(data)
                    # If config overrides ID, update it
                    if cfg_id and self._identity.device_id != cfg_id:
                        self._identity.device_id = cfg_id
                    return
            except Exception as exc:
                logger.warning("Could not read device storage at %s: %s", self.storage_path, exc)

        # 3. Create fresh persistent identity
        new_id = cfg_id or f"device-jarvis-{str(uuid.uuid4())[:8]}"
        self._identity = DeviceIdentity(
            device_id=new_id,
            device_name=cfg_name,
            device_version=app_ver,
            platform_os=f"{platform.system()} {platform.release()}",
            registered_at=datetime.now().isoformat(),
            last_seen=time.time(),
        )
        self.save()

    def update_last_seen(self) -> None:
        """Update last seen timestamp."""
        if self._identity:
            self._identity.last_seen = time.time()

    def save(self) -> None:
        """Persist device profile to JSON file."""
        if not self._identity:
            return
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self._identity.to_dict(), f, indent=2)
        except Exception as exc:
            logger.debug("Failed to write device file %s: %s", self.storage_path, exc)

    def get_registration_payload(self) -> Dict[str, Any]:
        """Return sanitized registration payload for Cloud Control Plane."""
        return {
            "device_id": self.identity.device_id,
            "device_name": self.identity.device_name,
            "device_version": self.identity.device_version,
            "platform_os": self.identity.platform_os,
            "registered_at": self.identity.registered_at,
        }


# Global DeviceManager singleton
device_manager = DeviceManager()
