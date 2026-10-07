"""Exception hierarchy for Secure Laptop <-> Vercel Cloud Communication (Phase 12).

Provides structured exceptions for connection, authentication, protocol, replay, and security failures.
"""


class CloudError(Exception):
    """Base exception for all cloud communication failures."""

    def __init__(self, message: str, code: str = "CLOUD_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class CloudAuthenticationError(CloudError):
    """Raised when authentication fails (missing/invalid token or signature)."""

    def __init__(self, message: str = "Cloud authentication failed.") -> None:
        super().__init__(message, code="CLOUD_AUTH_ERROR")


class CloudProtocolError(CloudError):
    """Raised when an incoming or outgoing message violates protocol schema."""

    def __init__(self, message: str = "Invalid cloud message protocol.") -> None:
        super().__init__(message, code="CLOUD_PROTOCOL_ERROR")


class CloudReplayError(CloudError):
    """Raised when a message replay attack or expired timestamp is detected."""

    def __init__(self, message: str = "Replay attack detected or timestamp expired.") -> None:
        super().__init__(message, code="CLOUD_REPLAY_ERROR")


class CloudConnectionError(CloudError):
    """Raised when network connection to cloud control plane fails."""

    def __init__(self, message: str = "Failed to connect to cloud control plane.") -> None:
        super().__init__(message, code="CLOUD_CONNECTION_ERROR")


class CloudTimeoutError(CloudError):
    """Raised when cloud request or heartbeat exceeds timeout."""

    def __init__(self, message: str = "Cloud request timed out.") -> None:
        super().__init__(message, code="CLOUD_TIMEOUT_ERROR")


class CloudSecurityError(CloudError):
    """Raised when an unsafe payload or unauthorized command is attempted."""

    def __init__(self, message: str = "Cloud command violates local security policy.") -> None:
        super().__init__(message, code="CLOUD_SECURITY_ERROR")


class CloudDeviceError(CloudError):
    """Raised when device identification or registration fails."""

    def __init__(self, message: str = "Device identity verification failed.") -> None:
        super().__init__(message, code="CLOUD_DEVICE_ERROR")
