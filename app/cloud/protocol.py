"""Strict message protocol and schema validation for Cloud <-> Laptop communication (Phase 12).

Defines typed dataclasses, serialization, timestamp tolerance checks, and replay cache.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
import time
from typing import Any, Dict, Optional, Set
import uuid

from app.cloud.errors import CloudProtocolError, CloudReplayError


class MessageType(str, Enum):
    """Supported cloud message types."""
    COMMAND = "command"
    RESPONSE = "response"
    HEARTBEAT = "heartbeat"
    STATUS = "status"
    PING = "ping"
    PONG = "pong"
    DISCONNECT = "disconnect"


class ResponseStatus(str, Enum):
    """Status outcomes for command execution responses."""
    SUCCESS = "success"
    ERROR = "error"
    CONFIRMATION_REQUIRED = "confirmation_required"
    REJECTED = "rejected"


@dataclass
class CloudMessage:
    """Envelope model for all messages exchanged between Laptop and Cloud."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = MessageType.COMMAND.value
    timestamp: float = field(default_factory=time.time)
    device_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    status: Optional[str] = None
    signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize message to dictionary."""
        d: Dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "timestamp": round(self.timestamp, 4),
            "device_id": self.device_id,
            "payload": self.payload,
        }
        if self.status is not None:
            d["status"] = self.status
        if self.signature is not None:
            d["signature"] = self.signature
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CloudMessage":
        """Parse and validate dictionary representation into a CloudMessage."""
        if not isinstance(data, dict):
            raise CloudProtocolError("Message payload must be a JSON object.")

        msg_id = str(data.get("id", "")).strip()
        if not msg_id:
            raise CloudProtocolError("Message 'id' field is required.")

        msg_type = str(data.get("type", "")).strip().lower()
        if not msg_type:
            raise CloudProtocolError("Message 'type' field is required.")

        timestamp = data.get("timestamp")
        if timestamp is None or not isinstance(timestamp, (int, float)):
            raise CloudProtocolError("Message 'timestamp' must be a numeric timestamp.")

        device_id = str(data.get("device_id", "")).strip()
        if not device_id:
            raise CloudProtocolError("Message 'device_id' is required.")

        payload = data.get("payload")
        if payload is None or not isinstance(payload, dict):
            raise CloudProtocolError("Message 'payload' must be a JSON object.")

        status = data.get("status")
        if status is not None:
            status = str(status).strip().lower()

        signature = data.get("signature")
        if signature is not None:
            signature = str(signature).strip()

        return cls(
            id=msg_id,
            type=msg_type,
            timestamp=float(timestamp),
            device_id=device_id,
            payload=payload,
            status=status,
            signature=signature,
        )


class ReplayProtection:
    """Sliding-window replay attack detector and timestamp validator."""

    def __init__(self, max_drift_seconds: float = 300.0, max_cache_size: int = 1000) -> None:
        self.max_drift_seconds = max_drift_seconds
        self.max_cache_size = max_cache_size
        self._seen_ids: Set[str] = set()
        self._id_timestamps: Dict[str, float] = {}

    def validate_message(self, message: CloudMessage, current_time: Optional[float] = None) -> None:
        """Validate that message timestamp is within acceptable window and has not been replayed.

        Raises:
            CloudReplayError: If timestamp is stale, too far in future, or ID was already processed.
        """
        now = current_time if current_time is not None else time.time()

        # 1. Timestamp Freshness Check
        diff = now - message.timestamp
        if diff > self.max_drift_seconds:
            raise CloudReplayError(
                f"Message expired: timestamp is {diff:.1f}s old (max allowed {self.max_drift_seconds}s)."
            )
        if diff < -30.0:  # Allow max 30s future clock skew
            raise CloudReplayError(
                f"Message timestamp is in the future by {-diff:.1f}s."
            )

        # 2. Duplicate ID Check
        if message.id in self._seen_ids:
            raise CloudReplayError(f"Duplicate message ID '{message.id}' detected (replay attack).")

        # 3. Cache ID
        self._record_id(message.id, message.timestamp, now)

    def _record_id(self, msg_id: str, msg_ts: float, now: float) -> None:
        """Store ID and prune stale IDs outside expiration window."""
        self._seen_ids.add(msg_id)
        self._id_timestamps[msg_id] = msg_ts

        # Prune older than 2 * max_drift_seconds if cache grows large
        if len(self._seen_ids) > self.max_cache_size:
            cutoff = now - (self.max_drift_seconds * 2)
            stale = [i for i, t in self._id_timestamps.items() if t < cutoff]
            for stale_id in stale:
                self._seen_ids.discard(stale_id)
                self._id_timestamps.pop(stale_id, None)

    def reset(self) -> None:
        """Clear cache (for testing or session reset)."""
        self._seen_ids.clear()
        self._id_timestamps.clear()
