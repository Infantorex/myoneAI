"""Activity tracker and event aggregator for myoneAI Web Dashboard (Phase 11).

Maintains an in-memory ring buffer of sanitized, safe system and user events.
Guarantees zero leakage of API keys, passwords, raw audio, or private contents.
"""

from datetime import datetime
import logging
import threading
import time
from typing import Any, Dict, List, Optional
import uuid

from app.core.events import Event, SystemEvent, ToolEvent, VoiceEvent, event_bus
from app.core.logging_config import SensitiveDataFilter

logger = logging.getLogger("myoneAI.web.activity")


class ActivityTracker:
    """Thread-safe event buffer capturing high-level assistant activity."""

    def __init__(self, max_items: int = 100) -> None:
        self.max_items = max_items
        self._items: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._filter = SensitiveDataFilter()
        self._subscribed = False
        self._init_subscriptions()

    def _init_subscriptions(self) -> None:
        """Subscribe to system event bus."""
        if self._subscribed:
            return

        # Seed with initial event
        self.record_event(
            event_type="SYSTEM",
            description="JARVIS Assistant subsystem initialized.",
            level="INFO",
        )

        try:
            event_bus.subscribe(SystemEvent.STATE_CHANGED, self._on_state_changed)
            event_bus.subscribe(VoiceEvent.WAKE_WORD_DETECTED, self._on_wake_word)
            event_bus.subscribe(VoiceEvent.LISTENING_STARTED, lambda e: self.record_event("VOICE", "Assistant started listening.", "INFO"))
            event_bus.subscribe(VoiceEvent.LISTENING_STOPPED, lambda e: self.record_event("VOICE", "Assistant stopped listening.", "INFO"))
            event_bus.subscribe(ToolEvent.TOOL_EXECUTED, self._on_tool_executed)
            event_bus.subscribe(ToolEvent.TOOL_FAILED, self._on_tool_failed)
            event_bus.subscribe("monitoring.alert", self._on_alert)
            self._subscribed = True
        except Exception as exc:
            logger.debug("Could not attach all event bus listeners: %s", exc)

    def _on_state_changed(self, event: Event) -> None:
        new_state = event.data.get("new_state", "")
        self.record_event("STATE", f"Assistant transitioned to {new_state.upper()}.", "INFO")

    def _on_wake_word(self, event: Event) -> None:
        self.record_event("VOICE", "Wake word detected. JARVIS activated.", "INFO")

    def _on_tool_executed(self, event: Event) -> None:
        tool_name = event.data.get("tool", "tool")
        self.record_event("TOOL", f"Tool '{tool_name}' executed successfully.", "INFO")

    def _on_tool_failed(self, event: Event) -> None:
        tool_name = event.data.get("tool", "tool")
        self.record_event("TOOL", f"Tool '{tool_name}' execution failed.", "WARNING")

    def _on_alert(self, event: Event) -> None:
        msg = event.data.get("message", "System threshold exceeded.")
        level = event.data.get("level", "WARNING")
        self.record_event("SYSTEM", msg, level)

    def record_event(
        self,
        event_type: str,
        description: str,
        level: str = "INFO",
    ) -> Dict[str, Any]:
        """Record a sanitized activity item."""
        # Sanitize text
        clean_desc = self._filter.mask_sensitive_text(description)
        now_dt = datetime.now().isoformat()
        item = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": now_dt,
            "event_type": event_type.upper(),
            "description": clean_desc,
            "level": level.upper(),
        }

        with self._lock:
            self._items.insert(0, item)
            if len(self._items) > self.max_items:
                self._items = self._items[:self.max_items]

        return item

    def get_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the most recent sanitized events."""
        with self._lock:
            return list(self._items[:limit])

    def clear(self) -> None:
        """Clear recorded events."""
        with self._lock:
            self._items.clear()


# Global ActivityTracker singleton
activity_tracker = ActivityTracker()
