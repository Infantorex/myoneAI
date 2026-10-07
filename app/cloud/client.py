"""Central Cloud Communication Client for Laptop <-> Vercel Cloud Plane (Phase 12).

Orchestrates connection, registration, periodic heartbeats, command routing with permission enforcement,
and safe offline queuing.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.cloud.authentication import sign_message, verify_message_signature
from app.cloud.connection import CloudConnection, ConnectionState
from app.cloud.device import DeviceManager, device_manager
from app.cloud.errors import (
    CloudAuthenticationError,
    CloudConnectionError,
    CloudProtocolError,
    CloudReplayError,
    CloudSecurityError,
)
from app.cloud.heartbeat import HeartbeatManager, heartbeat_manager
from app.cloud.protocol import CloudMessage, MessageType, ReplayProtection, ResponseStatus
from app.cloud.queue import OfflineEventQueue, offline_queue
from app.cloud.reconnect import ReconnectManager
from app.core.config import Settings, get_settings
from app.security.permissions import PermissionLevel, PermissionManager, permission_manager
from app.tools.executor import ToolExecutor, tool_executor
from app.tools.schemas import ToolCall

logger = logging.getLogger("myoneAI.cloud.client")


class CloudClient:
    """Orchestrates outbound cloud communication from the Windows laptop to Vercel Cloud Plane."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        connection: Optional[CloudConnection] = None,
        device: Optional[DeviceManager] = None,
        heartbeat: Optional[HeartbeatManager] = None,
        queue: Optional[OfflineEventQueue] = None,
        permissions: Optional[PermissionManager] = None,
        executor: Optional[ToolExecutor] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.connection = connection or CloudConnection(settings=self.settings)
        self.device = device or device_manager
        self.heartbeat = heartbeat or heartbeat_manager
        self.queue = queue or offline_queue
        self.permissions = permissions or permission_manager
        self.executor = executor or tool_executor

        self.reconnect_mgr = ReconnectManager(
            min_interval=self.settings.cloud_reconnect_min,
            max_interval=self.settings.cloud_reconnect_max,
        )
        self.replay_protection = ReplayProtection()

        self._heartbeat_task: Optional[asyncio.Task] = None
        self._poll_task: Optional[asyncio.Task] = None
        self._is_running: bool = False

    @property
    def is_connected(self) -> bool:
        """True if connection state is active."""
        return self.connection.is_connected

    @property
    def status(self) -> Dict[str, Any]:
        """Return diagnostic status snapshot."""
        return {
            "enabled": self.settings.cloud_enabled,
            "state": self.connection.state.value,
            "device_id": self.device.device_id,
            "device_name": self.device.identity.device_name,
            "queued_messages": self.queue.size,
            "reconnect_attempts": self.reconnect_mgr.attempts,
            "last_seen": self.device.identity.last_seen,
        }

    async def register_device(self) -> Dict[str, Any]:
        """Register device identity with cloud control plane."""
        reg_payload = self.device.get_registration_payload()
        msg = CloudMessage(
            type="register",
            device_id=self.device.device_id,
            payload=reg_payload,
        )
        secret = self.settings.cloud_auth_token.strip() if self.settings.cloud_auth_token else ""
        if secret:
            sign_message(secret, msg)

        res = await self.connection.post_message("/api/device/register", msg)
        logger.info("Successfully registered device '%s' with cloud.", self.device.device_id)
        return res

    async def send_heartbeat(self) -> Optional[Dict[str, Any]]:
        """Generate and transmit periodic system telemetry heartbeat."""
        msg = await self.heartbeat.build_heartbeat_message()
        try:
            res = await self.connection.post_message("/api/device/heartbeat", msg)
            self.device.update_last_seen()
            self.connection.set_state(ConnectionState.CONNECTED)
            self.reconnect_mgr.record_success()
            return res
        except Exception as exc:
            logger.debug("Heartbeat transmission failed: %s", exc)
            self.reconnect_mgr.record_failure()
            # Enqueue safe heartbeat snapshot to offline buffer
            try:
                self.queue.enqueue(msg)
            except Exception:
                pass
            return None

    async def flush_offline_queue(self) -> int:
        """Send pending buffered messages after re-establishing connectivity."""
        sent_count = 0
        while not self.queue.is_empty:
            msg = self.queue.dequeue()
            if not msg:
                break
            try:
                await self.connection.post_message("/api/device/response", msg)
                sent_count += 1
            except Exception as exc:
                logger.debug("Failed sending queued message: %s. Re-enqueuing.", exc)
                self.queue.enqueue(msg)
                break
        return sent_count

    async def handle_incoming_command(self, message: CloudMessage) -> CloudMessage:
        """Validate, check permissions, and execute a command received from Cloud.

        Guarantees:
        - Signature and token validation
        - Replay attack rejection
        - Permission tier compliance (SAFE, CONFIRM, BLOCKED)
        - Zero arbitrary shell execution
        """
        secret = self.settings.cloud_auth_token.strip() if self.settings.cloud_auth_token else ""
        
        # 1. Verify Signature
        if secret:
            verify_message_signature(secret, message)

        # 2. Replay Protection & Timestamp Freshness
        self.replay_protection.validate_message(message)

        # 3. Protocol & Payload Validation
        tool_name = message.payload.get("tool")
        arguments = message.payload.get("arguments", {})

        if not tool_name or not isinstance(tool_name, str):
            raise CloudProtocolError("Cloud command missing 'tool' name in payload.")
        if not isinstance(arguments, dict):
            raise CloudProtocolError("Cloud command 'arguments' must be a dictionary.")

        # 4. Check Permission Tier via PermissionManager
        perm_level, reason = self.permissions.evaluate_tool_permission(tool_name, arguments)

        if perm_level == PermissionLevel.BLOCKED:
            logger.warning("Cloud attempted to execute BLOCKED tool '%s'. Rejected. Reason: %s", tool_name, reason)
            return CloudMessage(
                id=message.id,
                type=MessageType.RESPONSE.value,
                device_id=self.device.device_id,
                status=ResponseStatus.REJECTED.value,
                payload={"error": f"Tool '{tool_name}' is permanently blocked by security policy. {reason}"},
            )

        if perm_level == PermissionLevel.CONFIRMATION_REQUIRED:
            logger.info("Cloud requested CONFIRM tool '%s'. User confirmation required.", tool_name)
            pending = self.permissions.create_pending_confirmation(
                tool_name=tool_name,
                arguments=arguments,
                prompt_message=f"Cloud requested action: {tool_name}",
            )
            return CloudMessage(
                id=message.id,
                type=MessageType.RESPONSE.value,
                device_id=self.device.device_id,
                status=ResponseStatus.CONFIRMATION_REQUIRED.value,
                payload={
                    "message": f"Action '{tool_name}' requires local user approval.",
                    "confirmation_token": pending.token,
                },
            )

        # 5. Execute SAFE Tool
        try:
            call = ToolCall(tool=tool_name, arguments=arguments)
            tool_res = await self.executor.execute(call)
            
            resp_status = ResponseStatus.SUCCESS.value if tool_res.success else ResponseStatus.ERROR.value
            resp_payload = {
                "success": tool_res.success,
                "message": tool_res.message,
                "data": tool_res.data,
            }
        except Exception as exc:
            logger.error("Error executing cloud tool '%s': %s", tool_name, exc)
            resp_status = ResponseStatus.ERROR.value
            resp_payload = {"success": False, "error": str(exc)}

        resp_msg = CloudMessage(
            id=message.id,
            type=MessageType.RESPONSE.value,
            device_id=self.device.device_id,
            status=resp_status,
            payload=resp_payload,
        )

        if secret:
            sign_message(secret, resp_msg)

        return resp_msg

    async def _heartbeat_loop(self) -> None:
        """Background loop dispatching periodic heartbeats and flushing offline queue."""
        interval = max(5, int(self.settings.cloud_heartbeat_interval))
        logger.info("Cloud heartbeat loop active (interval=%ds).", interval)

        while self._is_running:
            try:
                await self.send_heartbeat()
                await self.flush_offline_queue()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug("Error in cloud heartbeat loop: %s", exc)

            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break

    async def connect(self) -> bool:
        """Initialize connection, register device, and start background tasks."""
        if not self.settings.cloud_enabled:
            logger.info("Cloud communication is disabled (CLOUD_ENABLED=false).")
            return False

        self.connection.set_state(ConnectionState.CONNECTING)
        try:
            await self.register_device()
            self.connection.set_state(ConnectionState.CONNECTED)
            self._is_running = True
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            return True
        except Exception as exc:
            logger.warning("Cloud initial connection failed: %s. Will retry.", exc)
            self.connection.set_state(ConnectionState.RECONNECTING, str(exc))
            self._is_running = True
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            return False

    async def disconnect(self) -> None:
        """Gracefully disconnect and cancel background tasks."""
        self._is_running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

        await self.connection.close()
        logger.info("Cloud client disconnected gracefully.")


# Global cloud client singleton
cloud_client = CloudClient()
