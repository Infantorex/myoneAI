"""End-to-End Test: Dashboard / Cloud -> Local Agent -> Permission Manager -> Tool -> Cloud Response."""

import time
import pytest
from fastapi.testclient import TestClient

from app.cloud.authentication import sign_message
from app.cloud.client import CloudClient
from app.cloud.protocol import CloudMessage, MessageType
from web.api.server import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.mark.asyncio
async def test_cloud_to_local_agent_command_e2e():
    """Verify cloud control plane command dispatch -> local tool execution -> result feedback."""
    from app.security.permissions import PermissionManager
    from app.tools.executor import ToolExecutor
    from app.cloud.device import DeviceManager

    token = "test-secret-cloud-token-123456"
    device_mgr = DeviceManager()
    pm = PermissionManager()
    executor = ToolExecutor(permissions=pm)
    client = CloudClient(device=device_mgr, permissions=pm, executor=executor)

    # 1. Issue a signed command from cloud to laptop
    cmd_msg = CloudMessage(
        id="cmd_req_001",
        type=MessageType.COMMAND.value,
        device_id=device_mgr.device_id,
        payload={
            "tool": "get_battery_status",
            "arguments": {},
        },
    )
    signed_cmd = sign_message(token, cmd_msg)

    # 2. Local CloudClient receives, validates signature & permissions, executes tool
    res_msg = await client.handle_incoming_command(signed_cmd)

    # 3. Verify response
    assert res_msg.type == MessageType.RESPONSE.value
    assert res_msg.payload["success"] is True
    assert "battery" in str(res_msg.payload).lower() or "percent" in str(res_msg.payload).lower()
