"""Unit tests for Phase 4 AI Conversation Engine & Prompts."""

import asyncio
import pytest

from app.ai.errors import EmptyPromptError
from app.ai.manager import ConversationManager
from app.ai.models import ChatMessage
from app.ai.prompts import SYSTEM_PROMPT_TAMIL_JARVIS
from app.ai.provider import MockAIProvider


def test_system_prompt_tamil_persona():
    """Verify system prompt contains JARVIS personality, Tamil language rules, and safety boundaries."""
    assert "JARVIS" in SYSTEM_PROMPT_TAMIL_JARVIS
    assert "Infanto" in SYSTEM_PROMPT_TAMIL_JARVIS
    assert "Tamil" in SYSTEM_PROMPT_TAMIL_JARVIS


@pytest.mark.asyncio
async def test_conversation_manager_turn():
    """Verify ConversationManager processes turn and records assistant history."""
    provider = MockAIProvider(default_response="வணக்கம்! நான் உதவ தயார்.")
    mgr = ConversationManager(provider=provider, max_history_messages=10)

    reply = await mgr.respond("வணக்கம்")
    assert reply == "வணக்கம்! நான் உதவ தயார்."
    assert mgr.history_length == 2

    # Empty prompt rejection
    with pytest.raises(EmptyPromptError):
        await mgr.respond("   ")


def test_conversation_manager_clear_history():
    """Verify clear_history resets short-term conversational context."""
    mgr = ConversationManager(provider=MockAIProvider(), max_history_messages=5)
    mgr._history.append(ChatMessage(role="user", content="Hello"))
    assert mgr.history_length == 1
    mgr.clear_history()
    assert mgr.history_length == 0
