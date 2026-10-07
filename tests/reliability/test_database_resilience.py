"""Reliability: Database Missing/Corrupted File Handling."""

import sqlite3
from pathlib import Path
import pytest

from app.core.memory.store import SQLiteMemoryStore
from app.productivity.database import ProductivityDatabase


def test_sqlite_memory_store_creates_missing_parent_directories(tmp_path):
    """Verify SQLite store creates missing parent directories automatically."""
    deep_path = tmp_path / "deep" / "nested" / "dir" / "memory.db"
    assert not deep_path.parent.exists()

    store = SQLiteMemoryStore(db_path=deep_path)
    assert deep_path.exists()
    assert store.count() == 0


def test_productivity_database_creates_missing_tables_on_fresh_db(tmp_path):
    """Verify productivity database creates all schemas on fresh database."""
    fresh_db = tmp_path / "fresh_prod.db"
    db = ProductivityDatabase(db_path=str(fresh_db))
    
    conn = sqlite3.connect(str(fresh_db))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()

    assert "tasks" in tables
    assert "reminders" in tables
    assert "notes" in tables
