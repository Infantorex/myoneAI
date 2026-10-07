"""Event-driven publish-subscribe bus for myoneAI / Tamil JARVIS.

Enables decoupled communication between voice, AI, tools, monitoring, and state modules.
"""

import asyncio
import inspect
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger("myoneAI.events")


class SystemEvent(str, Enum):
    """Core system events."""
    STARTUP = "system.startup"
    SHUTDOWN = "system.shutdown"
    STATE_CHANGED = "system.state_changed"
    ERROR = "system.error"


class VoiceEvent(str, Enum):
    """Voice & Speech recognition/synthesis events."""
    WAKE_WORD_DETECTED = "voice.wake_word_detected"
    LISTENING_STARTED = "voice.listening_started"
    LISTENING_STOPPED = "voice.listening_stopped"
    SPEECH_TRANSCRIBED = "voice.speech_transcribed"
    TTS_STARTED = "voice.tts_started"
    TTS_FINISHED = "voice.tts_finished"


class AIEvent(str, Enum):
    """AI Conversation & reasoning events."""
    USER_MESSAGE = "ai.user_message"
    AI_RESPONSE = "ai.ai_response"
    INTENT_DETECTED = "ai.intent_detected"


class ToolEvent(str, Enum):
    """PC Tools & Execution events."""
    TOOL_REQUESTED = "tool.requested"
    CONFIRMATION_REQUIRED = "tool.confirmation_required"
    CONFIRMATION_RECEIVED = "tool.confirmation_received"
    TOOL_EXECUTED = "tool.executed"
    TOOL_FAILED = "tool.failed"


@dataclass
class Event:
    """Encapsulates an emitted event with timestamp and payload."""
    name: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


EventHandler = Callable[[Event], Any]


class EventBus:
    """Lightweight in-memory publish-subscribe event bus."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._all_subscribers: List[EventHandler] = []

    def subscribe(self, event_name: Union[str, Enum], handler: EventHandler) -> None:
        """Subscribe a callable handler to a specific event name or enum value."""
        key = event_name.value if isinstance(event_name, Enum) else event_name
        if handler not in self._subscribers[key]:
            self._subscribers[key].append(handler)
            logger.debug("Subscribed %s to event '%s'", getattr(handler, "__name__", str(handler)), key)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe a callable handler to all events."""
        if handler not in self._all_subscribers:
            self._all_subscribers.append(handler)

    def unsubscribe(self, event_name: Union[str, Enum], handler: EventHandler) -> bool:
        """Unsubscribe a callable handler from a specific event name."""
        key = event_name.value if isinstance(event_name, Enum) else event_name
        if key in self._subscribers and handler in self._subscribers[key]:
            self._subscribers[key].remove(handler)
            return True
        return False

    def emit(self, event_name: Union[str, Enum], data: Optional[Dict[str, Any]] = None) -> Event:
        """Synchronously emit an event to all registered listeners."""
        key = event_name.value if isinstance(event_name, Enum) else event_name
        event = Event(name=key, data=data or {})

        handlers = list(self._subscribers.get(key, [])) + list(self._all_subscribers)
        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    # Schedule coroutine if event loop is running
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(handler(event))
                    except RuntimeError:
                        asyncio.run(handler(event))
                else:
                    handler(event)
            except Exception as exc:
                logger.error("Error in event handler %s for '%s': %s", handler, key, exc, exc_info=True)

        return event

    async def emit_async(self, event_name: Union[str, Enum], data: Optional[Dict[str, Any]] = None) -> Event:
        """Asynchronously emit an event to all registered listeners."""
        key = event_name.value if isinstance(event_name, Enum) else event_name
        event = Event(name=key, data=data or {})

        handlers = list(self._subscribers.get(key, [])) + list(self._all_subscribers)
        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as exc:
                logger.error("Error in async event handler %s for '%s': %s", handler, key, exc, exc_info=True)

        return event

    def clear(self) -> None:
        """Clear all subscribers."""
        self._subscribers.clear()
        self._all_subscribers.clear()


# Global event bus singleton
event_bus = EventBus()
