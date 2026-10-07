"""Note-taking and notebook management business logic (Phase 10)."""

import logging
from typing import Any, Dict, List, Optional

from app.productivity.database import ProductivityDatabase, productivity_db
from app.productivity.models import NoteItem

logger = logging.getLogger("myoneAI.productivity.notes")


class NoteManager:
    """Manages user notes, tags, and search index."""

    def __init__(self, db: Optional[ProductivityDatabase] = None) -> None:
        self.db = db or productivity_db

    def create_note(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
    ) -> NoteItem:
        """Create and store a new user note."""
        if not title or not title.strip():
            # Derive title from first words of content
            words = content.strip().split()
            title = " ".join(words[:5]) if words else "Untitled Note"

        item = NoteItem(
            title=title.strip(),
            content=content.strip(),
            tags=tags or [],
        )
        saved = self.db.add_note(item)
        logger.info("Saved Note #%s: '%s'", saved.id, saved.title)
        return saved

    def get_note(self, note_id: int) -> Optional[NoteItem]:
        """Fetch note by numeric ID."""
        return self.db.get_note(note_id)

    def list_notes(self, limit: int = 20) -> List[NoteItem]:
        """List recently updated notes."""
        return self.db.list_notes(limit=limit)

    def search_notes(self, query: str, limit: int = 10) -> List[NoteItem]:
        """Search notes by title, content, or tag keyword match."""
        if not query or not query.strip():
            return []
        return self.db.search_notes(query.strip(), limit=limit)

    def update_note(
        self,
        note_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[NoteItem]:
        """Update existing note fields."""
        return self.db.update_note(
            note_id=note_id,
            title=title,
            content=content,
            tags=tags,
        )

    def delete_note(self, note_id: int) -> bool:
        """Delete note by ID."""
        return self.db.delete_note(note_id)

    def delete_note_by_title(self, title_query: str) -> Optional[NoteItem]:
        """Search note by title keyword and delete first match."""
        matches = self.search_notes(title_query, limit=1)
        if matches and matches[0].id is not None:
            deleted = self.db.delete_note(matches[0].id)
            if deleted:
                return matches[0]
        return None

    def clear_all_notes(self) -> int:
        """Clear all notes."""
        return self.db.clear_all_notes()


# Global NoteManager singleton
note_manager = NoteManager()
