"""Integration tests for Vercel Cloud Control Plane client sync and command handling."""

import time
import pytest

from app.cloud.authentication import sign_message
from app.cloud.client import CloudClient
from app.cloud.device import DeviceManager
from app.cloud.heartbeat import HeartbeatManager
from app.cloud.protocol import CloudMessage, MessageType
from app.security.permissions import PermissionManager
from app.tools.executor import ToolExecutor


@pytest.mark.asyncio
async def test_cloud_device_registration_and_heartbeat():
    """Verify device registration, authenticated heartbeats, and signed command handling."""
    device_mgr = DeviceManager()
    hb_mgr = HeartbeatManager(device=device_mgr)
    pm = PermissionManager()
    executor = ToolExecutor(permissions=pm)
    client = CloudClient(device=device_mgr, heartbeat=hb_mgr, permissions=pm, executor=executor)

    # 1. Verify Registration Payload
    reg_payload = device_mgr.get_registration_payload()
    assert "device_id" in reg_payload
    assert "platform_os" in reg_payload

    # 2. Verify Heartbeat Message Generation
    hb_msg = await hb_mgr.build_heartbeat_message()
    assert hb_msg.type == MessageType.HEARTBEAT.value
    assert "cpu_percent" in hb_msg.payload

    # 3. Test Incoming Safe Command via CloudClient
    cmd_msg = CloudMessage(
        type=MessageType.COMMAND.value,
        device_id=device_mgr.device_id,
        payload={"tool": "get_battery_status", "arguments": {}},
    )
    res_msg = await client.handle_incoming_command(cmd_msg)
    assert res_msg.type == MessageType.RESPONSE.value
    assert res_msg.payload["success"] is True

    # 4. Test Incoming Blocked Command via CloudClient
    blocked_cmd = CloudMessage(
        type=MessageType.COMMAND.value,
        device_id=device_mgr.device_id,
        payload={"tool": "execute_shell", "arguments": {"command": "dir"}},
    )
    blocked_res = await client.handle_incoming_command(blocked_cmd)
    assert blocked_res.type == MessageType.RESPONSE.value
    assert blocked_res.status == "rejected"
    assert "blocked" in blocked_res.payload["error"].lower()
