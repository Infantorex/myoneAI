"""Cloud Communication Layer for myoneAI / Tamil JARVIS (Phase 12).

Provides secure, outbound-only communication between the Windows laptop assistant
and the Vercel-hosted Cloud Control Plane with HMAC signing, replay protection,
and strict permission tier enforcement.
"""

from app.cloud.authentication import (
    compute_signature,
    generate_device_token,
    sign_message,
    verify_message_signature,
)
from app.cloud.client import CloudClient, cloud_client
from app.cloud.connection import CloudConnection, ConnectionState
from app.cloud.device import DeviceIdentity, DeviceManager, device_manager
from app.cloud.errors import (
    CloudAuthenticationError,
    CloudConnectionError,
    CloudDeviceError,
    CloudError,
    CloudProtocolError,
    CloudReplayError,
    CloudSecurityError,
    CloudTimeoutError,
)
from app.cloud.heartbeat import HeartbeatManager, heartbeat_manager
from app.cloud.protocol import (
    CloudMessage,
    MessageType,
    ReplayProtection,
    ResponseStatus,
)
from app.cloud.queue import OfflineEventQueue, offline_queue
from app.cloud.reconnect import ReconnectManager

__all__ = [
    # Models & Enums
    "MessageType",
    "ResponseStatus",
    "CloudMessage",
    "DeviceIdentity",
    "ConnectionState",
    # Exceptions
    "CloudError",
    "CloudAuthenticationError",
    "CloudProtocolError",
    "CloudReplayError",
    "CloudConnectionError",
    "CloudTimeoutError",
    "CloudSecurityError",
    "CloudDeviceError",
    # Authentication & Security
    "compute_signature",
    "sign_message",
    "verify_message_signature",
    "generate_device_token",
    "ReplayProtection",
    # Managers & Clients
    "DeviceManager",
    "device_manager",
    "HeartbeatManager",
    "heartbeat_manager",
    "OfflineEventQueue",
    "offline_queue",
    "ReconnectManager",
    "CloudConnection",
    "CloudClient",
    "cloud_client",
]
