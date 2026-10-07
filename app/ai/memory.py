"""Lightweight, privacy-aware memory system.

Separates short-term conversation context from minimal searchable long-term facts.
Never stores credentials, keys, or raw audio.
"""

from typing import Any, Dict, List, Optional


class MemoryManager:
    """Manages short-term conversation cache and explicit long-term user preferences."""

    def __init__(self) -> None:
        self._long_term_facts: Dict[str, Any] = {}

    def set_fact(self, key: str, value: Any) -> None:
        """Store an explicit user preference or fact."""
        self._long_term_facts[key] = value

    def get_fact(self, key: str, default: Optional[Any] = None) -> Any:
        """Retrieve a stored fact."""
        return self._long_term_facts.get(key, default)

    def delete_fact(self, key: str) -> bool:
        """Delete a stored fact."""
        if key in self._long_term_facts:
            del self._long_term_facts[key]
            return True
        return False

    def list_facts(self) -> Dict[str, Any]:
        """List all stored facts."""
        return dict(self._long_term_facts)

    def clear_all(self) -> None:
        """Clear all stored long-term memory."""
        self._long_term_facts.clear()
