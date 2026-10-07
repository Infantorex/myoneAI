"""Unit tests for Cloud Heartbeat telemetry generation (Phase 12)."""

import pytest

from app.cloud.heartbeat import HeartbeatManager
from app.core.config import Settings


@pytest.mark.asyncio
async def test_heartbeat_payload_generation():
    """Test generating a signed telemetry heartbeat message."""
    settings = Settings(
        cloud_device_id="test-laptop-1",
        cloud_auth_token="test-secret-token",
        app_version="1.0.0",
    )
    hm = HeartbeatManager(settings=settings)
    msg = await hm.build_heartbeat_message()

    assert msg.type == "heartbeat"
    assert msg.device_id == "test-laptop-1"
    assert msg.signature is not None
    assert "cpu_percent" in msg.payload
    assert "memory_percent" in msg.payload
    assert "disk_percent" in msg.payload
    assert "status" in msg.payload
    assert msg.payload["status"] == "online"
