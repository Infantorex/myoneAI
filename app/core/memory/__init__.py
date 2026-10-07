"""Controlled AI Memory module for myoneAI — Tamil JARVIS (Phase 7).

Provides privacy-aware, SQLite-backed persistent memory, contextual prompt retrieval,
and natural language memory command processing.
"""

from app.core.memory.manager import MemoryManager, memory_manager
from app.core.memory.models import MemoryCategory, MemoryItem, MemorySource
from app.core.memory.privacy import (
    SensitiveDataMemoryError,
    is_sensitive,
    validate_memory_content,
)
from app.core.memory.retrieval import MemoryRetriever
from app.core.memory.store import SQLiteMemoryStore

__all__ = [
    "MemoryCategory",
    "MemorySource",
    "MemoryItem",
    "SQLiteMemoryStore",
    "MemoryRetriever",
    "MemoryManager",
    "memory_manager",
    "is_sensitive",
    "validate_memory_content",
    "SensitiveDataMemoryError",
]
