"""Unit tests for Phase 1 Foundation: Config, Events, State Machine, Logging."""

import os
import pytest

from app.core.config import Settings, get_settings
from app.core.events import EventBus, VoiceEvent
from app.core.logging_config import SensitiveDataFilter, setup_logging
from app.core.state import AssistantState, StateManager


def test_settings_default_values():
    """Verify default configurations conform to specifications."""
    settings = get_settings()
    assert settings.app_name == "myoneAI"
    assert settings.jarvis_name == "JARVIS"
    assert settings.language == "ta-IN"
    assert settings.memory_enabled is True
    assert settings.tools_enabled is True
    assert settings.monitoring_enabled is True


def test_sensitive_data_filter():
    """Verify SensitiveDataFilter redacts tokens, passwords, and keys."""
    filter_inst = SensitiveDataFilter()
    raw = "User password=SuperSecret123 and token=abc123xyz456 and api_key=sk-1234567890abcdef"
    masked = filter_inst.mask_sensitive_text(raw)
    assert "SuperSecret123" not in masked
    assert "abc123xyz456" not in masked
    assert "[REDACTED]" in masked


def test_event_bus_subscribe_emit():
    """Verify EventBus publishes and dispatches synchronous and async events."""
    bus = EventBus()
    received = []

    def on_event(event):
        received.append(event.data)

    bus.subscribe("test.topic", on_event)
    bus.emit("test.topic", {"status": "ok"})

    assert len(received) == 1
    assert received[0]["status"] == "ok"


def test_state_machine_transitions():
    """Verify StateManager transitions correctly and records state changes."""
    sm = StateManager()
    assert sm.current_state == AssistantState.IDLE

    sm.set_state(AssistantState.LISTENING)
    assert sm.current_state == AssistantState.LISTENING

    sm.set_state(AssistantState.PROCESSING)
    assert sm.current_state == AssistantState.PROCESSING

    sm.set_state(AssistantState.SPEAKING)
    assert sm.current_state == AssistantState.SPEAKING

    sm.set_state(AssistantState.IDLE)
    assert sm.current_state == AssistantState.IDLE
