"""Unit tests for Phase 7 Controlled AI Memory System."""

import pytest

from app.core.memory.manager import MemoryManager
from app.core.memory.models import MemoryItem
from app.core.memory.privacy import validate_memory_content
from app.core.memory.store import SQLiteMemoryStore


def test_memory_privacy_rejection():
    """Verify sensitive credentials cannot be committed to memory store."""
    invalid_cases = [
        ("my_login", "password: Secret12345"),
        ("api_key", "sk-12345678901234567890abcdef"),
        ("otp_code", "otp: 987654"),
        ("card_info", "4111 2222 3333 4444"),
    ]
    for k, v in invalid_cases:
        is_valid, msg = validate_memory_content(k, v)
        assert is_valid is False
        assert msg is not None


@pytest.mark.asyncio
async def test_memory_crud_cycle(tmp_path):
    """Verify MemoryManager remembers, updates, retrieves, and forgets facts."""
    db_file = tmp_path / "unit_mem.db"
    mgr = MemoryManager(db_path=db_file)

    # 1. Remember
    item = await mgr.remember(
        category="project",
        key="main_project",
        value="Vibrawave AI Platform",
    )
    assert item.id is not None
    assert item.value == "Vibrawave AI Platform"

    # 2. Get Context
    ctx = mgr.get_context_for_prompt("What is my main project?")
    assert "Vibrawave" in ctx

    # 3. Delete
    deleted = await mgr.delete(category="project", key="main_project")
    assert deleted is True
    res = await mgr.get("project", "main_project")
    assert res is None
