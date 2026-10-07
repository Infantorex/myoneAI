"""Conversation Manager orchestrating short-term context, persona prompts, and AI provider inference.

Guarantees bounded memory usage, input/output validation, and non-crashing error handling.
"""

import asyncio
import logging
import re
from typing import List, Optional

from app.ai.errors import AIError, AIResponseError, EmptyPromptError
from app.ai.models import AIRequestConfig, ChatMessage
from app.ai.prompts import SYSTEM_PROMPT_TAMIL_JARVIS
from app.ai.provider import BaseAIProvider, get_ai_provider
from app.core.config import get_settings
from app.core.events import AIEvent, event_bus

logger = logging.getLogger("myoneAI.ai.manager")


class ConversationManager:
    """Manages short-term conversation history, prompt construction, and AI responses."""

    def __init__(
        self,
        provider: Optional[BaseAIProvider] = None,
        max_history_messages: Optional[int] = None,
        system_prompt: Optional[str] = None,
        request_config: Optional[AIRequestConfig] = None,
    ) -> None:
        settings = get_settings()
        self.provider = provider or get_ai_provider()
        self.max_history_messages = max_history_messages or settings.ai_max_history_messages
        self.system_prompt = system_prompt or SYSTEM_PROMPT_TAMIL_JARVIS
        self.request_config = request_config or AIRequestConfig(
            temperature=settings.ai_temperature,
            max_output_tokens=settings.ai_max_output_tokens,
            timeout_sec=settings.ai_timeout,
        )
        self._history: List[ChatMessage] = []
        self._lock = asyncio.Lock()

    @property
    def history_length(self) -> int:
        """Return the number of messages currently stored in short-term history."""
        return len(self._history)

    def get_history(self) -> List[ChatMessage]:
        """Return a copy of the short-term conversation history."""
        return list(self._history)

    def get_history_dicts(self) -> List[dict]:
        """Return conversation history as a list of role-content dictionaries."""
        return [msg.to_dict() for msg in self._history]

    def clear_history(self) -> None:
        """Reset short-term conversation context."""
        self._history.clear()
        logger.debug("Conversation context cleared.")

    @staticmethod
    def sanitize_input(text: str) -> str:
        """Validate and clean user input text."""
        if not text:
            raise EmptyPromptError("User message cannot be empty.")
        cleaned = re.sub(r"\s+", " ", text).strip()
        if not cleaned:
            raise EmptyPromptError("User message contains only whitespace.")
        return cleaned

    def _trim_history(self) -> None:
        """Keep only the most recent N messages (FIFO) to enforce bounded memory."""
        if len(self._history) > self.max_history_messages:
            excess = len(self._history) - self.max_history_messages
            self._history = self._history[excess:]
            logger.debug("Trimmed %d older messages from conversation context.", excess)

    async def respond(self, user_text: str) -> str:
        """Process user input, maintain short-term context, and generate assistant response.

        Args:
            user_text: Spoken or typed user input string.

        Returns:
            Clean conversational assistant response text.

        Raises:
            EmptyPromptError: If user_text is blank.
            AIError: On provider error, timeout, or validation failure.
        """
        clean_prompt = self.sanitize_input(user_text)

        async with self._lock:
            # 1. Append user message to short-term history
            user_msg = ChatMessage(role="user", content=clean_prompt)
            self._history.append(user_msg)
            self._trim_history()

            event_bus.emit(AIEvent.USER_MESSAGE, {"text": clean_prompt})

            # 2. Build payload for provider
            messages_payload = [m.to_dict() for m in self._history]

            logger.info("Generating AI reply (Context size: %d messages)...", len(messages_payload))

            # 3. Call AI provider
            try:
                ai_resp = await self.provider.generate(
                    messages=messages_payload,
                    system_prompt=self.system_prompt,
                    config=self.request_config,
                )
            except Exception as exc:
                logger.error("AI generation failed: %s", exc)
                # Remove the user message if provider failed so context isn't polluted
                if self._history and self._history[-1] is user_msg:
                    self._history.pop()
                raise

            # 4. Validate response
            reply_text = ai_resp.content.strip()
            if not reply_text:
                if self._history and self._history[-1] is user_msg:
                    self._history.pop()
                raise AIResponseError("AI provider returned blank response.")

            # 5. Append assistant turn
            assistant_msg = ChatMessage(role="assistant", content=reply_text)
            self._history.append(assistant_msg)
            self._trim_history()

            event_bus.emit(AIEvent.AI_RESPONSE, {"text": reply_text, "provider": ai_resp.provider})
            return reply_text

    def respond_sync(self, user_text: str) -> str:
        """Synchronous wrapper for conversation manager."""
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, self.respond(user_text))
                return future.result()
        except RuntimeError:
            return asyncio.run(self.respond(user_text))


# Global conversation manager singleton
conversation_manager = ConversationManager()
