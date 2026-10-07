"""SQLite storage engine for the Controlled AI Memory System (Phase 7).

Lightweight, persistent, zero-heavy-dependencies local database storage.
"""

import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.memory.models import MemoryItem

logger = logging.getLogger("myoneAI.memory.store")


class SQLiteMemoryStore:
    """Thread-safe SQLite storage engine for structured memories."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or get_settings().memory_db_path
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with row factory and performance pragmas."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Performance Pragmas for low RAM & fast disk I/O
        if str(self.db_path) != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA cache_size = -2000;")  # ~2MB cache
        conn.execute("PRAGMA temp_store = MEMORY;")
        return conn

    def _init_db(self) -> None:
        """Initialize SQLite database tables and indexes."""
        with self._lock:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        id TEXT PRIMARY KEY,
                        category TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        source TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        UNIQUE(category, key)
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_category ON memories (category)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_key ON memories (key)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_updated ON memories (updated_at DESC)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_cat_key ON memories (category, key)")
                conn.commit()
            logger.debug("Memory SQLite database initialized at '%s'", self.db_path)

    def save(self, item: MemoryItem) -> MemoryItem:
        """Insert or update a memory record (upsert on category + key)."""
        now = time.time()
        with self._lock:
            with self._get_connection() as conn:
                # Check if item with (category, key) already exists
                cursor = conn.execute(
                    "SELECT id, created_at FROM memories WHERE category = ? AND key = ?",
                    (item.category.lower(), item.key.lower()),
                )
                existing = cursor.fetchone()

                if existing:
                    item_id = existing["id"]
                    created_at = existing["created_at"]
                    conn.execute(
                        """
                        UPDATE memories
                        SET value = ?, source = ?, confidence = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (item.value, item.source, item.confidence, now, item_id),
                    )
                    item.id = item_id
                    item.created_at = created_at
                    item.updated_at = now
                    logger.info("Updated existing memory (Category: %s, Key: %s).", item.category, item.key)
                else:
                    item.created_at = now
                    item.updated_at = now
                    conn.execute(
                        """
                        INSERT INTO memories (id, category, key, value, source, confidence, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item.id,
                            item.category.lower(),
                            item.key.lower(),
                            item.value,
                            item.source,
                            item.confidence,
                            item.created_at,
                            item.updated_at,
                        ),
                    )
                    logger.info("Inserted new memory (Category: %s, Key: %s).", item.category, item.key)

                conn.commit()
        return item

    def get(self, category: str, key: str) -> Optional[MemoryItem]:
        """Retrieve a memory item by category and key."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM memories WHERE category = ? AND key = ?",
                    (category.lower(), key.lower()),
                )
                row = cursor.fetchone()
                if row:
                    return self._row_to_item(row)
        return None

    def get_by_id(self, item_id: str) -> Optional[MemoryItem]:
        """Retrieve a memory item by unique ID."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM memories WHERE id = ?", (item_id,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_item(row)
        return None

    def list_all(self, limit: int = 100, category: Optional[str] = None) -> List[MemoryItem]:
        """List all stored memory items, optionally filtered by category."""
        with self._lock:
            with self._get_connection() as conn:
                if category:
                    cursor = conn.execute(
                        "SELECT * FROM memories WHERE category = ? ORDER BY updated_at DESC LIMIT ?",
                        (category.lower(), limit),
                    )
                else:
                    cursor = conn.execute(
                        "SELECT * FROM memories ORDER BY updated_at DESC LIMIT ?",
                        (limit,),
                    )
                rows = cursor.fetchall()
                return [self._row_to_item(r) for r in rows]

    def search(self, query: str, limit: int = 10, category: Optional[str] = None) -> List[MemoryItem]:
        """Perform keyword search across memory keys, values, and categories."""
        q_wildcard = f"%{query.lower()}%"
        with self._lock:
            with self._get_connection() as conn:
                if category:
                    cursor = conn.execute(
                        """
                        SELECT * FROM memories
                        WHERE category = ? AND (key LIKE ? OR value LIKE ?)
                        ORDER BY updated_at DESC LIMIT ?
                        """,
                        (category.lower(), q_wildcard, q_wildcard, limit),
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT * FROM memories
                        WHERE key LIKE ? OR value LIKE ? OR category LIKE ?
                        ORDER BY updated_at DESC LIMIT ?
                        """,
                        (q_wildcard, q_wildcard, q_wildcard, limit),
                    )
                rows = cursor.fetchall()
                return [self._row_to_item(r) for r in rows]

    def delete(
        self,
        category: Optional[str] = None,
        key: Optional[str] = None,
        item_id: Optional[str] = None,
    ) -> bool:
        """Delete specific memory items by id or category/key."""
        with self._lock:
            with self._get_connection() as conn:
                if item_id:
                    cursor = conn.execute("DELETE FROM memories WHERE id = ?", (item_id,))
                elif category and key:
                    cursor = conn.execute(
                        "DELETE FROM memories WHERE category = ? AND key = ?",
                        (category.lower(), key.lower()),
                    )
                elif category:
                    cursor = conn.execute(
                        "DELETE FROM memories WHERE category = ?",
                        (category.lower(),),
                    )
                elif key:
                    cursor = conn.execute(
                        "DELETE FROM memories WHERE key = ?",
                        (key.lower(),),
                    )
                else:
                    return False
                conn.commit()
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info("Deleted memory (id=%s, category=%s, key=%s)", item_id, category, key)
                return deleted

    def clear_all(self) -> int:
        """Delete all memory records."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM memories")
                conn.commit()
                count = cursor.rowcount
                logger.info("Cleared all %d memory records from database.", count)
                return count

    def count(self) -> int:
        """Return total count of stored memory records."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) as cnt FROM memories")
                row = cursor.fetchone()
                return int(row["cnt"]) if row else 0

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> MemoryItem:
        """Convert a SQLite Row to a MemoryItem object."""
        return MemoryItem(
            id=row["id"],
            category=row["category"],
            key=row["key"],
            value=row["value"],
            source=row["source"],
            confidence=row["confidence"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
