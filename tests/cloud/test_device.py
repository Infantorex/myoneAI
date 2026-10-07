"""Unit tests for Device Identity & Registration (Phase 12)."""

from pathlib import Path
import tempfile
import pytest

from app.cloud.device import DeviceIdentity, DeviceManager
from app.core.config import Settings


def test_device_identity_serialization():
    """Test DeviceIdentity serialization to/from dictionary."""
    data = {
        "device_id": "test-device-123",
        "device_name": "MyOneAI-TestLaptop",
        "device_version": "1.0.0",
        "platform_os": "Windows 11",
        "registered_at": "2026-10-07T12:00:00",
        "last_seen": 1775570000.0,
    }
    identity = DeviceIdentity.from_dict(data)
    assert identity.device_id == "test-device-123"
    assert identity.device_name == "MyOneAI-TestLaptop"

    serialized = identity.to_dict()
    assert serialized["device_id"] == "test-device-123"
    assert serialized["last_seen"] == 1775570000.0


def test_device_manager_initialization_in_temp_dir():
    """Test DeviceManager loads or initializes identity without hardware secret leakage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Path(tmpdir) / "device.json"
        settings = Settings(cloud_device_id="custom-dev-id", cloud_device_name="Test-Laptop")
        
        dm = DeviceManager(settings=settings, storage_path=storage)
        assert dm.device_id == "custom-dev-id"
        assert dm.identity.device_name == "Test-Laptop"
        assert storage.exists()

        # Reload from disk
        dm2 = DeviceManager(settings=settings, storage_path=storage)
        assert dm2.device_id == "custom-dev-id"

        payload = dm.get_registration_payload()
        assert payload["device_id"] == "custom-dev-id"
        assert payload["device_name"] == "Test-Laptop"
        # Ensure no sensitive system secrets are present
        assert "password" not in payload
        assert "mac_address" not in payload
