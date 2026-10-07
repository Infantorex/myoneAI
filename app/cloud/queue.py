"""Thread-safe bounded offline event queue for Cloud Communication (Phase 12).

Buffers safe telemetry and synchronization events when internet is disconnected.
Strictly forbids queuing passwords, API keys, raw audio, or sensitive files.
"""

from collections import deque
import logging
import threading
from typing import Any, Dict, List, Optional

from app.cloud.errors import CloudSecurityError
from app.cloud.protocol import CloudMessage
from app.core.logging_config import SensitiveDataFilter

logger = logging.getLogger("myoneAI.cloud.queue")


class OfflineEventQueue:
    """Bounded, thread-safe in-memory queue for offline event synchronization."""

    def __init__(self, max_size: int = 100) -> None:
        self.max_size = max_size
        self._queue: deque[CloudMessage] = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._filter = SensitiveDataFilter()

    @property
    def size(self) -> int:
        """Return current number of queued messages."""
        with self._lock:
            return len(self._queue)

    @property
    def is_empty(self) -> bool:
        """Check if queue has zero items."""
        with self._lock:
            return len(self._queue) == 0

    def enqueue(self, message: CloudMessage) -> bool:
        """Add a safe message to the offline queue with privacy checks.

        Returns True if enqueued, or raises CloudSecurityError on unsafe content.
        """
        # 1. Validate payload does not contain banned keywords
        payload_str = str(message.payload).lower()
        banned = ["password", "api_key", "raw_audio", "screenshot_bytes", "web_auth_token", "private_key"]
        for b in banned:
            if b in payload_str:
                logger.warning("Rejected queuing event containing sensitive term '%s'", b)
                raise CloudSecurityError(f"Cannot enqueue event containing sensitive field '{b}'.")

        with self._lock:
            if len(self._queue) >= self.max_size:
                logger.debug("Offline queue is at max capacity (%d). Evicting oldest message.", self.max_size)
            self._queue.append(message)
            return True

    def dequeue(self) -> Optional[CloudMessage]:
        """Pop and return the oldest queued message, or None if empty."""
        with self._lock:
            if self._queue:
                return self._queue.popleft()
            return None

    def peek_all(self) -> List[CloudMessage]:
        """Return a snapshot of all queued messages without removing them."""
        with self._lock:
            return list(self._queue)

    def clear(self) -> int:
        """Empty the queue and return the number of discarded messages."""
        with self._lock:
            count = len(self._queue)
            self._queue.clear()
            return count


# Global offline queue singleton
offline_queue = OfflineEventQueue()
