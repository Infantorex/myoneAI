"""Connection state management and outbound transport for Cloud Communication (Phase 12).

Maintains connection lifecycle (DISCONNECTED, CONNECTING, CONNECTED, RECONNECTING, ERROR)
and performs secure outbound HTTPS requests.
"""

from enum import Enum
import logging
from typing import Any, Dict, Optional
import httpx

from app.cloud.errors import CloudConnectionError, CloudSecurityError, CloudTimeoutError
from app.cloud.protocol import CloudMessage
from app.core.config import Settings, get_settings

logger = logging.getLogger("myoneAI.cloud.connection")


class ConnectionState(str, Enum):
    """Lifecycle states of the outbound cloud connection."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class CloudConnection:
    """Manages the outbound HTTPS transport and connection state to the Cloud Control Plane."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._state: ConnectionState = ConnectionState.DISCONNECTED
        self._client: Optional[httpx.AsyncClient] = None
        self._last_error: Optional[str] = None

    @property
    def state(self) -> ConnectionState:
        """Return the current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """True if the connection state is CONNECTED."""
        return self._state == ConnectionState.CONNECTED

    def set_state(self, new_state: ConnectionState, error_message: Optional[str] = None) -> None:
        """Transition connection state and record error if any."""
        old_state = self._state
        self._state = new_state
        self._last_error = error_message
        if old_state != new_state:
            logger.info("Cloud connection state transitioned: %s -> %s", old_state.value, new_state.value)

    def _get_base_url(self) -> str:
        """Extract and validate the cloud API base URL."""
        url = self.settings.cloud_api_url.strip() if self.settings.cloud_api_url else ""
        if not url:
            raise CloudConnectionError("CLOUD_API_URL is not configured.")

        # TLS enforcement rule:
        if self.settings.cloud_tls_required and not url.startswith("https://"):
            # Allow http only for local loopback testing
            if not ("127.0.0.1" in url or "localhost" in url):
                raise CloudSecurityError("CLOUD_TLS_REQUIRED is enabled. URL must use HTTPS scheme.")
        return url.rstrip("/")

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create the underlying persistent HTTP client."""
        if self._client is None or self._client.is_closed:
            timeout = httpx.Timeout(self.settings.cloud_request_timeout, connect=5.0)
            self._client = httpx.AsyncClient(timeout=timeout)
        return self._client

    async def post_message(self, endpoint: str, message: CloudMessage) -> Dict[str, Any]:
        """Send an outbound POST request with a CloudMessage payload."""
        base_url = self._get_base_url()
        url = f"{base_url}{endpoint}" if endpoint.startswith("/") else f"{base_url}/{endpoint}"
        client = await self.get_client()

        headers = {
            "Content-Type": "application/json",
        }
        if self.settings.cloud_auth_token:
            headers["Authorization"] = f"Bearer {self.settings.cloud_auth_token}"

        try:
            response = await client.post(url, json=message.to_dict(), headers=headers)
            if response.status_code >= 400:
                raise CloudConnectionError(f"Cloud API error ({response.status_code}): {response.text}")
            return response.json()
        except httpx.TimeoutException as exc:
            self.set_state(ConnectionState.ERROR, "Request timed out")
            raise CloudTimeoutError(f"Request to '{url}' timed out: {exc}")
        except httpx.RequestError as exc:
            self.set_state(ConnectionState.ERROR, str(exc))
            raise CloudConnectionError(f"Network error communicating with '{url}': {exc}")

    async def close(self) -> None:
        """Close the underlying HTTP client transport."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        self._client = None
        self.set_state(ConnectionState.DISCONNECTED)
