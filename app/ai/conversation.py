"""Conversation Manager for maintaining dialogue state and context window.
"""

from typing import Any, Dict, List, Optional
from app.ai.provider import BaseAIProvider, AIResponse
from app.ai.prompts import SYSTEM_PROMPT_TAMIL_JARVIS


class ConversationManager:
    """Manages multi-turn conversation history and system instructions."""

    def __init__(
        self,
        provider: Optional[BaseAIProvider] = None,
        max_history_turns: int = 10,
    ) -> None:
        self.provider = provider
        self.max_history_turns = max_history_turns
        self.history: List[Dict[str, str]] = []

    def add_user_message(self, content: str) -> None:
        """Add a user turn to short-term history."""
        self.history.append({"role": "user", "content": content})
        self._trim_history()

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant turn to short-term history."""
        self.history.append({"role": "assistant", "content": content})
        self._trim_history()

    def _trim_history(self) -> None:
        """Keep only the most recent dialogue turns to minimize token/memory usage."""
        max_messages = self.max_history_turns * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]

    def clear_history(self) -> None:
        """Clear short-term conversation context."""
        self.history.clear()

    async def get_response(
        self,
        user_input: str,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[AIResponse]:
        """Process user input and get response from AI provider."""
        if not self.provider:
            return None

        self.add_user_message(user_input)
        response = await self.provider.generate_response(
            messages=self.history,
            tools=tools,
            system_instruction=SYSTEM_PROMPT_TAMIL_JARVIS,
        )
        if response and response.content:
            self.add_assistant_message(response.content)
        return response
