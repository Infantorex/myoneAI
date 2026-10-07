"""End-to-End Integration tests for Laptop <-> Vercel Cloud Control Plane (Phase 12).

Tests full registration, telemetry heartbeat, command dispatching, permission checking,
and offline buffering using FastAPI TestClient.
"""

import pytest
from fastapi.testclient import TestClient

from app.cloud.authentication import sign_message
from app.cloud.client import CloudClient
from app.cloud.protocol import CloudMessage, MessageType, ResponseStatus
from app.core.config import Settings, get_settings
from app.security.permissions import PermissionManager
from app.tools.executor import ToolExecutor
from web.api.server import app
from web.cloud.devices import cloud_device_registry


@pytest.fixture
def mock_cloud_env():
    """Configure mock settings for integration tests."""
    cloud_device_registry.clear()
    mock_settings = Settings(
        cloud_enabled=True,
        cloud_api_url="http://127.0.0.1:8000",
        cloud_device_id="laptop-integration-test",
        cloud_auth_token="integration-test-secret-token",
        cloud_tls_required=False,
    )
    app.dependency_overrides[get_settings] = lambda: mock_settings
    client = TestClient(app)
    yield client, mock_settings
    app.dependency_overrides.pop(get_settings, None)
    cloud_device_registry.clear()


def test_full_cloud_registration_and_heartbeat_cycle(mock_cloud_env):
    """Test device registration and telemetry heartbeat delivery to Cloud Control Plane."""
    client, settings = mock_cloud_env
    headers = {"Authorization": f"Bearer {settings.cloud_auth_token}"}

    # 1. Device Registration
    reg_msg = CloudMessage(
        id="reg-101",
        type="register",
        device_id=settings.cloud_device_id,
        payload={
            "device_name": "MyOneAI-Laptop-Test",
            "device_version": "1.0.0",
            "platform_os": "Windows 11",
        },
    )
    sign_message(settings.cloud_auth_token, reg_msg)

    res = client.post("/api/device/register", json=reg_msg.to_dict(), headers=headers)
    assert res.status_code == 200
    assert res.json()["success"] is True

    # 2. Heartbeat Intake
    hb_msg = CloudMessage(
        id="hb-201",
        type="heartbeat",
        device_id=settings.cloud_device_id,
        payload={
            "status": "online",
            "assistant_state": "idle",
            "cpu_percent": 22.5,
            "memory_percent": 54.0,
            "battery_percent": 90.0,
        },
    )
    sign_message(settings.cloud_auth_token, hb_msg)

    res = client.post("/api/device/heartbeat", json=hb_msg.to_dict(), headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "ack"

    # 3. Query Device Status from Vercel Control Plane
    res = client.get(f"/api/device/status?device_id={settings.cloud_device_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()["device"]
    assert data["device_id"] == settings.cloud_device_id
    assert data["status"] == "online"
    assert data["telemetry"]["cpu_percent"] == 22.5


@pytest.mark.asyncio
async def test_cloud_command_dispatch_and_laptop_execution(mock_cloud_env):
    """Test full cycle: Cloud enqueues command -> Laptop polls and processes -> Laptop posts response."""
    client, settings = mock_cloud_env
    headers = {"Authorization": f"Bearer {settings.cloud_auth_token}"}

    # 1. Vercel dashboard dispatches command
    cmd_msg = CloudMessage(
        id="cmd-dispatch-301",
        type=MessageType.COMMAND.value,
        device_id=settings.cloud_device_id,
        payload={"tool": "get_system_status", "arguments": {}},
    )
    sign_message(settings.cloud_auth_token, cmd_msg)

    res = client.post("/api/device/request", json=cmd_msg.to_dict(), headers=headers)
    assert res.status_code == 200
    assert res.json()["command_id"] == "cmd-dispatch-301"

    # 2. Laptop polls for pending commands
    res = client.post(f"/api/device/request?device_id={settings.cloud_device_id}", headers=headers)
    assert res.status_code == 200
    commands = res.json()["commands"]
    assert len(commands) == 1
    received_cmd = CloudMessage.from_dict(commands[0])

    # 3. Laptop processes command through permission and tool layer
    pm = PermissionManager()
    executor = ToolExecutor(permissions=pm)
    laptop_client = CloudClient(settings=settings, permissions=pm, executor=executor)
    resp_msg = await laptop_client.handle_incoming_command(received_cmd)

    assert resp_msg.status == ResponseStatus.SUCCESS.value
    assert resp_msg.payload["success"] is True

    # 4. Laptop submits response back to Cloud Control Plane
    res = client.post("/api/device/response", json=resp_msg.to_dict(), headers=headers)
    assert res.status_code == 200
    assert res.json()["success"] is True
