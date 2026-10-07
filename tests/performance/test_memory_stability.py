"""Memory Stability & Leak Detection Tests."""

import gc
import tracemalloc
import pytest

from app.core.memory.manager import MemoryManager
from app.core.memory.models import MemoryItem
from app.core.memory.store import SQLiteMemoryStore


def test_sqlite_memory_stability_under_repeated_ops(tmp_path):
    """Verify SQLiteMemoryStore does not leak memory over 100 insertions and queries."""
    tracemalloc.start()
    db_file = tmp_path / "leak_test.db"
    store = SQLiteMemoryStore(db_path=db_file)

    mem_before, _ = tracemalloc.get_traced_memory()

    for i in range(100):
        store.save(MemoryItem(
            category="project",
            key=f"item_{i}",
            value=f"value {i}",
            source="user",
            confidence=1.0,
        ))
        _ = store.get("project", f"item_{i}")

    gc.collect()
    mem_after, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Peak memory during 100 SQLite operations should stay under 2 MB
    assert (peak / (1024 * 1024)) < 2.0
