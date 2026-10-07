"""Relevant memory retrieval and prompt context builder for AI (Phase 7).

Retrieves only contextual memories matching the user prompt, adhering strictly
to token and character limits (MEMORY_MAX_RESULTS and MEMORY_MAX_CONTEXT_CHARS).
"""

import logging
import re
from typing import List, Optional

from app.core.config import get_settings
from app.core.memory.models import MemoryItem
from app.core.memory.store import SQLiteMemoryStore

logger = logging.getLogger("myoneAI.memory.retrieval")

# Stop words to ignore during query tokenization
STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "is",
    "are", "was", "were", "what", "which", "who", "whom", "this", "that", "these",
    "those", "my", "your", "his", "her", "its", "our", "their", "me", "you",
    "tell", "know", "about", "do", "does", "did", "can", "could", "should", "would",
    "இன்று", "என்ன", "எப்படி", "எங்கே", "யார்", "எனது", "உனது", "பற்றி",
}


class MemoryRetriever:
    """Retrieves relevant memories and constructs bounded prompt contexts."""

    def __init__(self, store: SQLiteMemoryStore) -> None:
        self.store = store

    def retrieve_relevant(
        self,
        query: str,
        max_results: Optional[int] = None,
        max_chars: Optional[int] = None,
    ) -> List[MemoryItem]:
        """Retrieve relevant memory records ranked by keyword and contextual relevance.

        Args:
            query: User's input prompt.
            max_results: Maximum number of memory items to return.
            max_chars: Maximum aggregate character length for retrieved items.

        Returns:
            List of relevant MemoryItem objects.
        """
        settings = get_settings()
        limit = max_results or settings.memory_max_results
        char_limit = max_chars or settings.memory_max_context_chars

        if not query or not query.strip():
            return []

        all_memories = self.store.list_all(limit=200)
        if not all_memories:
            return []

        # Tokenize query
        clean_tokens = [
            t.lower() for t in re.findall(r"[\w\u0B80-\u0BFF]+", query)
            if len(t) > 1 and t.lower() not in STOP_WORDS
        ]

        if not clean_tokens:
            # If only stop words, return top preferences if available
            scored = [(item, 1.0) for item in all_memories if item.category in ("preference", "project")]
        else:
            scored = []
            for item in all_memories:
                score = self._calculate_relevance(clean_tokens, item)
                if score > 0.0:
                    scored.append((item, score))

            # Sort by score descending, then by updated_at descending
            scored.sort(key=lambda x: (x[1], x[0].updated_at), reverse=True)

        selected: List[MemoryItem] = []
        current_chars = 0

        for item, _ in scored[:limit]:
            item_chars = len(item.to_prompt_str())
            if current_chars + item_chars > char_limit:
                break
            selected.append(item)
            current_chars += item_chars

        logger.debug("Retrieved %d relevant memories for query '%s'", len(selected), query[:30])
        return selected

    def build_memory_context_prompt(
        self,
        query: str,
        max_results: Optional[int] = None,
        max_chars: Optional[int] = None,
    ) -> str:
        """Format retrieved memories into a structured context block for the AI system prompt.

        Returns empty string if no relevant memories exist.
        """
        memories = self.retrieve_relevant(query, max_results=max_results, max_chars=max_chars)
        if not memories:
            return ""

        lines = ["\n[Saved User Context & Preferences]:"]
        for m in memories:
            lines.append(m.to_prompt_str())

        lines.append("[End Saved Context]\n")
        return "\n".join(lines)

    @staticmethod
    def _calculate_relevance(tokens: List[str], item: MemoryItem) -> float:
        """Calculate relevance score between query tokens and a memory item."""
        score = 0.0
        item_text = f"{item.category} {item.key} {item.value}".lower()
        key_text = item.key.lower().replace("_", " ")

        for token in tokens:
            # Exact match in key (e.g. 'project' in 'main_project')
            if token in key_text:
                score += 3.0
            # Exact match in value (e.g. 'Vibrawave' in value)
            if token in item.value.lower():
                score += 2.5
            # Category match (e.g. 'preference')
            if token in item.category.lower():
                score += 1.5
            # Substring match
            elif token in item_text:
                score += 1.0

        # Preference bias: general user preferences get a small baseline weight
        if item.category == "preference":
            score += 0.2

        return score
