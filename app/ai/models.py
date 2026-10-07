"""Data models and schemas for AI conversation and messaging.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ChatMessage:
    """Represents a single turn in a multi-turn conversation."""
    role: str  # "system", "user", "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, str]:
        """Convert to standard role-content dictionary."""
        return {"role": self.role, "content": self.content}


@dataclass
class AIRequestConfig:
    """Parameters governing AI generation."""
    temperature: float = 0.7
    max_output_tokens: int = 500
    timeout_sec: float = 30.0


@dataclass
class AIResponse:
    """Standardized response from an AI provider."""
    content: str
    provider: str = "unknown"
    model: str = "unknown"
    duration_sec: float = 0.0
    usage: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        return self.content
