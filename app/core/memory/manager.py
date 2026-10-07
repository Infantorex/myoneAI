"""Central Memory Manager for myoneAI — Tamil JARVIS (Phase 7).

Coordinates privacy validation, SQLite persistence, relevance retrieval, and natural language memory command parsing.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.core.memory.models import MemoryCategory, MemoryItem, MemorySource
from app.core.memory.privacy import (
    PRIVACY_REJECTION_MESSAGE,
    PRIVACY_REJECTION_MESSAGE_TAMIL,
    SensitiveDataMemoryError,
    validate_memory_content,
)
from app.core.memory.retrieval import MemoryRetriever, STOP_WORDS
from app.core.memory.store import SQLiteMemoryStore

logger = logging.getLogger("myoneAI.memory.manager")


class MemoryManager:
    """Manages the lifecycle of user preferences, project facts, and persistent context."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.settings = get_settings()
        self.store = SQLiteMemoryStore(db_path=db_path or self.settings.memory_db_path)
        self.retriever = MemoryRetriever(store=self.store)
        self._pending_clear_confirmation = False

    async def remember(
        self,
        category: str,
        key: str,
        value: str,
        source: str = MemorySource.USER.value,
        confidence: float = 1.0,
    ) -> MemoryItem:
        """Store or update a structured memory item with privacy validation.

        Args:
            category: Category (e.g. 'preference', 'project', 'personal_context', 'instruction').
            key: Canonical key identifier (e.g. 'main_project', 'language_preference').
            value: The fact or preference string.
            source: Origin source.
            confidence: Confidence score.

        Returns:
            Saved MemoryItem.

        Raises:
            SensitiveDataMemoryError: If sensitive credentials or private info are detected.
            ValueError: If key or value is blank.
        """
        is_valid, err_msg = validate_memory_content(key, value)
        if not is_valid:
            logger.warning("Rejected memory write: %s", err_msg)
            raise SensitiveDataMemoryError(err_msg)

        item = MemoryItem(
            category=category.lower(),
            key=key.lower().strip(),
            value=value.strip(),
            source=source,
            confidence=confidence,
        )
        return self.store.save(item)

    async def get(self, category: str, key: str) -> Optional[MemoryItem]:
        """Retrieve a specific memory item by category and key."""
        return self.store.get(category, key)

    async def get_by_id(self, item_id: str) -> Optional[MemoryItem]:
        """Retrieve a specific memory item by unique ID."""
        return self.store.get_by_id(item_id)

    async def update(self, category: str, key: str, value: str) -> MemoryItem:
        """Update an existing memory item."""
        return await self.remember(category=category, key=key, value=value)

    async def search(self, query: str, limit: int = 10, category: Optional[str] = None) -> List[MemoryItem]:
        """Search memory items matching a keyword query."""
        return self.store.search(query, limit=limit, category=category)

    async def list_all(self, limit: int = 100, category: Optional[str] = None) -> List[MemoryItem]:
        """List all stored memory items."""
        return self.store.list_all(limit=limit, category=category)

    async def delete(
        self,
        category: Optional[str] = None,
        key: Optional[str] = None,
        item_id: Optional[str] = None,
    ) -> bool:
        """Delete specific memory records."""
        return self.store.delete(category=category, key=key, item_id=item_id)

    async def clear(self, confirmed: bool = False) -> int:
        """Clear all stored memories with mandatory confirmation safeguard.

        Args:
            confirmed: Must be True to proceed with full deletion.

        Returns:
            Count of deleted memory records.

        Raises:
            PermissionError: If confirmation is required but not provided.
        """
        if self.settings.memory_require_confirmation and not confirmed:
            raise PermissionError("Clear all memories requires explicit user confirmation.")

        count = self.store.clear_all()
        self._pending_clear_confirmation = False
        return count

    def get_context_for_prompt(self, user_query: str) -> str:
        """Build relevant memory context string for AI prompt injection."""
        if not self.settings.memory_enabled:
            return ""
        return self.retriever.build_memory_context_prompt(user_query)

    async def process_memory_command(self, text: str) -> Optional[str]:
        """Parse natural language user commands and execute memory actions if detected.

        Returns:
            Conversational response string if handled, or None if prompt is a regular conversation.
        """
        if not text or not text.strip():
            return None

        clean = text.strip()
        clean_lower = clean.lower()

        # 1. Inspection Commands ("What do you remember about me?")
        if re.search(r"(?i)\bwhat\s+do\s+you\s+remember\b|\bwhat\s+memories\b|\bshow\s+my\s+memories\b|என்னை\s+பற்றி\s+என்ன\s+நினைவிருக்கிறது", clean_lower):
            memories = await self.list_all()
            if not memories:
                return "I don't have any saved memories yet.\nஉங்களைப்பற்றி என்னிடம் எந்த தகவலும் சேமிக்கப்படவில்லை."

            lines = ["I remember the following details:\nநினைவில் உள்ள தகவல்கள்:"]
            for m in memories:
                lines.append(m.to_display_str())
            return "\n".join(lines)

        # 2. Clear All Memories Commands
        if re.search(r"(?i)\b(?:clear|erase|delete|wipe)\s+(?:all\s+)?(?:my\s+)?memories\b|\ball\s+memories\s+clear\b|எல்லா\s+நினைவுகளையும்\s+அழி", clean_lower):
            if not self._pending_clear_confirmation:
                self._pending_clear_confirmation = True
                return (
                    "This will permanently delete all your saved memories. Are you sure? "
                    "Say 'Yes, clear memories' to confirm.\n"
                    "இது உங்கள் அனைத்து நினைவுகளையும் நிரந்தரமாக நீக்கும். அழிக்க விரும்புகிறீர்களா?"
                )
            else:
                count = await self.clear(confirmed=True)
                return f"All {count} memories have been permanently cleared.\nஅனைத்து நினைவுகளும் அழிக்கப்பட்டன."

        if self._pending_clear_confirmation:
            if re.search(r"(?i)\b(?:yes|confirm|sure|proceed|ஆமாம்|சரி)\b", clean_lower):
                count = await self.clear(confirmed=True)
                return f"Confirmed. All {count} memories have been cleared.\nஅனைத்து நினைவுகளும் அழிக்கப்பட்டன."
            else:
                self._pending_clear_confirmation = False
                return "Memory deletion cancelled.\nநினைவு அழிப்பு ரத்து செய்யப்பட்டது."

        # 3. Explicit Remember Commands ("Remember that my project is Vibrawave")
        remember_match = re.search(
            r"(?i)\b(?:remember\s+that|remember|don't\s+forget\s+that|don't\s+forget|keep\s+in\s+mind\s+that)\s+(.+)",
            clean,
        )
        tamil_remember_match = re.search(r"(.+)\s+(?:நினைவில்\s+வைத்துக்கொள்|நினைவில்\s+வை)", clean)

        if remember_match or tamil_remember_match:
            statement = remember_match.group(1).strip() if remember_match else tamil_remember_match.group(1).strip()
            category, key, value = self._extract_memory_triplet(statement)

            try:
                item = await self.remember(category=category, key=key, value=value)
                return f"சரி, இதை நினைவில் வைத்துக்கொள்கிறேன்: {item.key.replace('_', ' ')} = {item.value}"
            except SensitiveDataMemoryError:
                return PRIVACY_REJECTION_MESSAGE_TAMIL

        # 4. Explicit Forget Commands ("Forget that my project is Vibrawave", "Forget my project information")
        forget_match = re.search(
            r"(?i)\b(?:forget\s+that|forget\s+my|forget\s+about|forget|remove\s+memory)\s+(.+)",
            clean,
        )
        if forget_match:
            target = forget_match.group(1).strip().lower()
            # Try finding matches by key or value
            matched = await self.search(target)
            if not matched:
                # Try simple token search
                tokens = [w for w in target.split() if w not in STOP_WORDS]
                for t in tokens:
                    matched.extend(await self.search(t))

            if matched:
                deleted_keys = []
                for item in matched[:3]:
                    await self.delete(category=item.category, key=item.key)
                    deleted_keys.append(item.key.replace("_", " "))
                return f"மறந்துவிட்டேன் (Deleted memory): {', '.join(deleted_keys)}"
            else:
                return f"I couldn't find any saved memory matching '{target}'.\nஇது போன்ற எந்த தகவலும் நினைவில் இல்லை."

        return None

    @staticmethod
    def _extract_memory_triplet(statement: str) -> Tuple[str, str, str]:
        """Infer category, canonical key, and value from a remember statement."""
        st_clean = statement.strip()
        st_lower = st_clean.lower()

        # Project patterns
        if "project" in st_lower or "திட்டம்" in st_lower:
            match = re.search(r"(?i)(?:my\s+project(?:\s+name)?(?:\s+is)?(?:\s+called)?)\s+([A-Za-z0-9_\-\s]+)", st_clean)
            val = match.group(1).strip() if match else st_clean
            val = re.sub(r"(?i)^is\s+called\s+|^is\s+", "", val).strip()
            return MemoryCategory.PROJECT.value, "main_project", val or st_clean

        # Language preference patterns
        if "tamil" in st_lower or "தமிழ்" in st_lower:
            return MemoryCategory.PREFERENCE.value, "language_preference", "Tamil"
        if "english" in st_lower or "ஆங்கிலம்" in st_lower:
            return MemoryCategory.PREFERENCE.value, "language_preference", "English"

        # Response style patterns
        if "short answer" in st_lower or "concise" in st_lower or "சுருக்கமாக" in st_lower:
            return MemoryCategory.PREFERENCE.value, "response_style", "short concise answers"

        # General key-value matching ("my X is Y")
        match_is = re.search(r"(?i)(?:my|the)\s+([A-Za-z0-9_\s]{2,20})\s+is\s+(.+)", st_clean)
        if match_is:
            raw_k = match_is.group(1).strip().replace(" ", "_").lower()
            raw_v = match_is.group(2).strip()
            return MemoryCategory.PERSONAL_CONTEXT.value, raw_k, raw_v

        # Fallback general instruction
        return MemoryCategory.INSTRUCTION.value, "general_note", st_clean


# Global Memory Manager singleton
memory_manager = MemoryManager()
