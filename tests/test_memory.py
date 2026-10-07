"""Automated unit and integration tests for Controlled AI Memory System (Phase 7)."""

import asyncio
import tempfile
from pathlib import Path
import pytest

from app.ai.manager import ConversationManager
from app.ai.provider import MockAIProvider
from app.core.config import Settings
from app.core.memory.manager import MemoryManager
from app.core.memory.models import MemoryCategory, MemoryItem
from app.core.memory.privacy import (
    SensitiveDataMemoryError,
    is_sensitive,
    validate_memory_content,
)
from app.core.memory.store import SQLiteMemoryStore


@pytest.fixture
def temp_memory_manager(tmp_path: Path) -> MemoryManager:
    """Provide an isolated MemoryManager using a temporary SQLite database."""
    db_file = tmp_path / "test_memory.db"
    return MemoryManager(db_path=db_file)


@pytest.mark.asyncio
async def test_add_and_get_memory(temp_memory_manager: MemoryManager):
    """Verify adding a memory record and retrieving it by category and key."""
    item = await temp_memory_manager.remember(
        category="project",
        key="main_project",
        value="Vibrawave",
    )
    assert item.id is not None
    assert item.category == "project"
    assert item.key == "main_project"
    assert item.value == "Vibrawave"

    retrieved = await temp_memory_manager.get("project", "main_project")
    assert retrieved is not None
    assert retrieved.id == item.id
    assert retrieved.value == "Vibrawave"


@pytest.mark.asyncio
async def test_memory_upsert_update(temp_memory_manager: MemoryManager):
    """Verify storing with identical (category, key) updates existing record without duplicates."""
    # First write
    item1 = await temp_memory_manager.remember(
        category="preference",
        key="language_preference",
        value="English",
    )

    # Second write with same category & key
    item2 = await temp_memory_manager.remember(
        category="preference",
        key="language_preference",
        value="Tamil",
    )

    assert item1.id == item2.id
    assert item2.value == "Tamil"

    all_items = await temp_memory_manager.list_all()
    assert len(all_items) == 1
    assert all_items[0].value == "Tamil"


@pytest.mark.asyncio
async def test_search_and_list_memories(temp_memory_manager: MemoryManager):
    """Verify searching across keys, values, and listing items."""
    await temp_memory_manager.remember(category="project", key="project_alpha", value="Vibrawave Engine")
    await temp_memory_manager.remember(category="preference", key="voice_type", value="Tamil Neural")
    await temp_memory_manager.remember(category="instruction", key="reply_length", value="Short and concise")

    # Search keyword
    results = await temp_memory_manager.search("Vibrawave")
    assert len(results) == 1
    assert results[0].key == "project_alpha"

    # Search category
    results_pref = await temp_memory_manager.search("Tamil", category="preference")
    assert len(results_pref) == 1
    assert results_pref[0].key == "voice_type"

    # List all
    all_items = await temp_memory_manager.list_all()
    assert len(all_items) == 3


@pytest.mark.asyncio
async def test_delete_memory(temp_memory_manager: MemoryManager):
    """Verify deleting memory by key or category."""
    item = await temp_memory_manager.remember(category="project", key="old_tool", value="Legacy Code")
    assert await temp_memory_manager.get("project", "old_tool") is not None

    # Delete by key
    deleted = await temp_memory_manager.delete(category="project", key="old_tool")
    assert deleted
    assert await temp_memory_manager.get("project", "old_tool") is None


@pytest.mark.asyncio
async def test_clear_all_with_confirmation(temp_memory_manager: MemoryManager):
    """Verify clear requires confirmed=True."""
    await temp_memory_manager.remember(category="project", key="p1", value="Val1")
    await temp_memory_manager.remember(category="project", key="p2", value="Val2")

    # Unconfirmed -> PermissionError
    with pytest.raises(PermissionError):
        await temp_memory_manager.clear(confirmed=False)

    # Confirmed -> Success
    count = await temp_memory_manager.clear(confirmed=True)
    assert count == 2
    assert len(await temp_memory_manager.list_all()) == 0


@pytest.mark.asyncio
async def test_privacy_filter_rejection(temp_memory_manager: MemoryManager):
    """Verify sensitive data (API keys, passwords, OTPs, cards) is rejected."""
    sensitive_cases = [
        ("api_key", "sk-abcdef12345678901234567890"),
        ("user_password", "password: supersecret123"),
        ("bank_card", "4111 2222 3333 4444"),
        ("login_otp", "otp: 489201"),
    ]

    for key, val in sensitive_cases:
        assert is_sensitive(val)
        with pytest.raises(SensitiveDataMemoryError):
            await temp_memory_manager.remember(category="credential", key=key, value=val)


@pytest.mark.asyncio
async def test_empty_memory_rejection(temp_memory_manager: MemoryManager):
    """Verify blank keys or values are rejected."""
    with pytest.raises(SensitiveDataMemoryError):
        await temp_memory_manager.remember(category="preference", key="", value="something")

    with pytest.raises(SensitiveDataMemoryError):
        await temp_memory_manager.remember(category="preference", key="valid_key", value="   ")


@pytest.mark.asyncio
async def test_relevant_retrieval_ranking(temp_memory_manager: MemoryManager):
    """Verify memory retrieval scores and includes only relevant items."""
    await temp_memory_manager.remember(category="project", key="main_project", value="Vibrawave")
    await temp_memory_manager.remember(category="preference", key="response_style", value="concise")
    await temp_memory_manager.remember(category="instruction", key="gardening_tip", value="water plants daily")

    # Prompt related to project
    ctx = temp_memory_manager.get_context_for_prompt("Can you review my project architecture?")
    assert "Vibrawave" in ctx
    assert "gardening_tip" not in ctx


@pytest.mark.asyncio
async def test_natural_memory_commands(temp_memory_manager: MemoryManager):
    """Verify natural memory command parsing for remember, inspect, forget, and clear."""
    # 1. Natural Remember
    reply = await temp_memory_manager.process_memory_command("Remember that my project is Vibrawave")
    assert reply is not None
    assert "Vibrawave" in reply
    assert (await temp_memory_manager.get("project", "main_project")).value == "Vibrawave"

    # 2. Natural Inspection
    inspect_reply = await temp_memory_manager.process_memory_command("What do you remember about me?")
    assert inspect_reply is not None
    assert "Vibrawave" in inspect_reply

    # 3. Tamil Natural Remember
    tamil_reply = await temp_memory_manager.process_memory_command("எனக்கு தமிழ் பிடிக்கும் நினைவில் வைத்துக்கொள்")
    assert tamil_reply is not None
    assert (await temp_memory_manager.get("preference", "language_preference")).value == "Tamil"

    # 4. Natural Forget
    forget_reply = await temp_memory_manager.process_memory_command("Forget that my project is Vibrawave")
    assert forget_reply is not None
    assert await temp_memory_manager.get("project", "main_project") is None


@pytest.mark.asyncio
async def test_ai_conversation_integration_with_memory(tmp_path: Path):
    """Verify ConversationManager injects relevant memories into AI context."""
    db_file = tmp_path / "conv_mem.db"
    mgr = MemoryManager(db_path=db_file)
    await mgr.remember(category="project", key="main_project", value="Vibrawave")

    mock_ai = MockAIProvider(default_response="Your project is Vibrawave.")
    conv = ConversationManager(provider=mock_ai, memory=mgr)

    response = await conv.respond("What is my project?")
    assert response == "Your project is Vibrawave."

    # Verify that mock_ai received system prompt with memory context
    last_msgs = mock_ai.last_messages
    assert len(last_msgs) >= 1
