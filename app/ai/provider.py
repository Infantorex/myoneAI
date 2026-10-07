"""Abstract AI Provider interface for cloud LLM inference.

Decouples the assistant from any specific AI provider (Gemini, OpenAI, Anthropic, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolCall:
    """Represents a tool or PC control action requested by the AI."""
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIResponse:
    """Standardized response from the AI provider."""
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    raw_response: Optional[Any] = None


class BaseAIProvider(ABC):
    """Abstract interface for AI inference providers."""

    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_instruction: Optional[str] = None,
    ) -> AIResponse:
        """Send prompt to cloud LLM and receive structured response.

        Args:
            messages: Conversation history.
            tools: Optional tool/function schemas.
            system_instruction: Persona and behavioral guidelines.

        Returns:
            AIResponse object with text response and optional tool calls.
        """
        pass
