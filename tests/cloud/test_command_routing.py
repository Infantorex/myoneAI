"""Unit tests for Cloud Command Routing & Permission Enforcement (Phase 12)."""

import pytest

from app.cloud.authentication import sign_message
from app.cloud.client import CloudClient
from app.cloud.errors import CloudAuthenticationError, CloudReplayError
from app.cloud.protocol import CloudMessage, MessageType, ResponseStatus
from app.core.config import Settings
from app.security.permissions import PermissionLevel, PermissionManager
from app.tools.executor import ToolExecutor


@pytest.fixture
def client_instance():
    settings = Settings(
        cloud_device_id="laptop-route-test",
        cloud_auth_token="route-test-secret-123",
        app_version="1.0.0",
    )
    pm = PermissionManager()
    executor = ToolExecutor(permissions=pm)
    return CloudClient(settings=settings, permissions=pm, executor=executor)


@pytest.mark.asyncio
async def test_safe_command_execution(client_instance):
    """Test that a SAFE command executes successfully through ToolExecutor."""
    secret = client_instance.settings.cloud_auth_token
    msg = CloudMessage(
        id="cmd-safe-1",
        type=MessageType.COMMAND.value,
        device_id="laptop-route-test",
        payload={"tool": "get_system_status", "arguments": {}},
    )
    sign_message(secret, msg)

    response = await client_instance.handle_incoming_command(msg)
    assert response.id == "cmd-safe-1"
    assert response.status == ResponseStatus.SUCCESS.value
    assert response.payload["success"] is True
    assert "data" in response.payload


@pytest.mark.asyncio
async def test_confirm_tier_requires_local_confirmation(client_instance):
    """Test that a CONFIRM tool is NOT executed automatically and requires user approval."""
    secret = client_instance.settings.cloud_auth_token
    msg = CloudMessage(
        id="cmd-confirm-1",
        type=MessageType.COMMAND.value,
        device_id="laptop-route-test",
        payload={"tool": "close_application", "arguments": {"process_name": "notepad"}},
    )
    sign_message(secret, msg)

    response = await client_instance.handle_incoming_command(msg)
    assert response.id == "cmd-confirm-1"
    assert response.status == ResponseStatus.CONFIRMATION_REQUIRED.value
    assert "confirmation_token" in response.payload


@pytest.mark.asyncio
async def test_blocked_tier_rejected(client_instance):
    """Test that a BLOCKED tool is rejected immediately."""
    secret = client_instance.settings.cloud_auth_token

    msg = CloudMessage(
        id="cmd-blocked-1",
        type=MessageType.COMMAND.value,
        device_id="laptop-route-test",
        payload={"tool": "execute_shell", "arguments": {"command": "dir"}},
    )
    sign_message(secret, msg)

    response = await client_instance.handle_incoming_command(msg)
    assert response.id == "cmd-blocked-1"
    assert response.status == ResponseStatus.REJECTED.value
    assert "permanently blocked" in response.payload["error"]


@pytest.mark.asyncio
async def test_invalid_signature_rejected(client_instance):
    """Test that tampered or invalid signatures are rejected."""
    msg = CloudMessage(
        id="cmd-bad-sig",
        type=MessageType.COMMAND.value,
        device_id="laptop-route-test",
        payload={"tool": "get_system_status", "arguments": {}},
        signature="invalid-hmac-signature",
    )

    with pytest.raises(CloudAuthenticationError):
        await client_instance.handle_incoming_command(msg)
