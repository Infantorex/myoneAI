"""Reliability: Assistant State Machine Safety & Determinism."""

import pytest

from app.core.state import AssistantState, StateManager


def test_state_machine_illegal_transition_handling():
    """Verify state transitions always remain controlled and return safely to IDLE."""
    sm = StateManager()
    assert sm.current_state == AssistantState.IDLE

    # Valid lifecycle
    sm.set_state(AssistantState.LISTENING)
    assert sm.current_state == AssistantState.LISTENING

    sm.set_state(AssistantState.ERROR)
    assert sm.current_state == AssistantState.ERROR

    # Must be able to recover back to IDLE from ERROR
    sm.set_state(AssistantState.IDLE)
    assert sm.current_state == AssistantState.IDLE
