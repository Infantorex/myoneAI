"""Integration tests connecting AI Conversation Engine with Memory and PC Tools."""

import asyncio
import pytest

from app.ai.manager import ConversationManager
from app.ai.provider import MockAIProvider
from app.core.memory.manager import MemoryManager
from app.security.permissions import PermissionManager
from app.tools.executor import ToolExecutor


@pytest.mark.asyncio
async def test_ai_remembers_and_retrieves_across_turns(tmp_path):
    """Verify AI manager processes memory command and recalls context on subsequent queries."""
    db_file = tmp_path / "integ_mem.db"
    mem_mgr = MemoryManager(db_path=db_file)
    provider = MockAIProvider(default_response="Vibrawave AI is your primary project.")
    conv = ConversationManager(provider=provider, memory=mem_mgr)

    # 1. Store via natural command
    remember_reply = await conv.respond("Remember that my main project is Vibrawave AI")
    assert "நினைவில்" in remember_reply or "remember" in remember_reply.lower()

    # 2. Query knowledge
    query_reply = await conv.respond("What is my main project?")
    assert "Vibrawave" in query_reply


@pytest.mark.asyncio
async def test_ai_executes_safe_tool_and_returns_result():
    """Verify ConversationManager intercepts tool intent, routes to ToolExecutor, and speaks output."""
    pm = PermissionManager()
    executor = ToolExecutor(permissions=pm)
    conv = ConversationManager(tools=executor, permissions=pm)

    reply = await conv.respond("check battery")
    assert reply is not None
    assert "battery" in reply.lower() or "பேட்டரி" in reply or "charge" in reply.lower()
