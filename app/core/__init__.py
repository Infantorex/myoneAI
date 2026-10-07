"""Core module for myoneAI / Tamil JARVIS.

Handles configuration, structured logging, event pub-sub, state tracking, and lifecycle.
"""

from app.core.config import Settings, get_settings
from app.core.events import EventBus, Event, SystemEvent, event_bus
from app.core.logging_config import setup_logging
from app.core.state import AssistantState, StateManager, state_manager

__all__ = [
    "Settings",
    "get_settings",
    "EventBus",
    "Event",
    "SystemEvent",
    "event_bus",
    "setup_logging",
    "AssistantState",
    "StateManager",
    "state_manager",
]
