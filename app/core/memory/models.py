"""Data models and schemas for the Controlled AI Memory System (Phase 7)."""

import time
import uuid
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class MemoryCategory(str, Enum):
    """Categorization for stored memories."""
    PREFERENCE = "preference"
    PROJECT = "project"
    PERSONAL_CONTEXT = "personal_context"
    INSTRUCTION = "instruction"
    TASK = "task"


class MemorySource(str, Enum):
    """Origin source of the stored memory."""
    USER = "user"
    INFERRED = "assistant_inferred"


class MemoryItem(BaseModel):
    """Structured memory record."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str = Field(default=MemoryCategory.PREFERENCE.value, description="Memory category")
    key: str = Field(..., description="Canonical key/topic identifier (e.g., 'main_project')")
    value: str = Field(..., description="Memory content/fact (e.g., 'Vibrawave')")
    source: str = Field(default=MemorySource.USER.value, description="Origin source")
    confidence: float = Field(default=1.0, description="Confidence score (0.0 - 1.0)")
    created_at: float = Field(default_factory=time.time, description="Creation epoch timestamp")
    updated_at: float = Field(default_factory=time.time, description="Last update epoch timestamp")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize memory record to dictionary."""
        return self.model_dump()

    def to_prompt_str(self) -> str:
        """Format as a concise prompt context line for the AI model."""
        return f"- [{self.category.capitalize()}] {self.key}: {self.value}"

    def to_display_str(self) -> str:
        """Format as a human-friendly string for user display."""
        clean_key = self.key.replace("_", " ").capitalize()
        return f"• {clean_key}: {self.value}"
