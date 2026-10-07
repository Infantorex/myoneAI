"""Pytest fixtures configuration."""

import os
import tempfile
from pathlib import Path
import pytest

from app.core.config import Settings, get_settings
from app.core.memory.manager import MemoryManager
from app.core.memory.store import SQLiteMemoryStore
from app.productivity.database import ProductivityDatabase
from app.productivity.manager import ProductivityManager
from app.security.permissions import PermissionManager
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry


@pytest.fixture
def clean_temp_dir(tmp_path):
    """Provide a dedicated isolated temporary directory."""
    return tmp_path


@pytest.fixture
def mock_memory_manager(tmp_path):
    """Provide an isolated MemoryManager backed by temporary SQLite DB."""
    db_file = tmp_path / "fixture_memory.db"
    store = SQLiteMemoryStore(db_path=db_file)
    return MemoryManager(db_path=db_file)


@pytest.fixture
def mock_productivity_db(tmp_path):
    """Provide an isolated ProductivityDatabase in temporary directory."""
    db_file = tmp_path / "fixture_productivity.db"
    return ProductivityDatabase(db_path=str(db_file))


@pytest.fixture
def mock_productivity_manager(mock_productivity_db):
    """Provide an isolated ProductivityManager."""
    return ProductivityManager(database=mock_productivity_db)


@pytest.fixture
def mock_permission_manager():
    """Provide a clean PermissionManager."""
    return PermissionManager()


@pytest.fixture
def mock_tool_executor(mock_permission_manager):
    """Provide a clean ToolExecutor with default registry."""
    return ToolExecutor(permissions=mock_permission_manager)
