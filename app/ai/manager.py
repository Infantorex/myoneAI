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
from app.core.memory.manager import MemoryManager, memory_manager
from app.security.permissions import PermissionManager, permission_manager
from app.tools.executor import ToolExecutor, tool_executor
from app.tools.intent import parse_tool_intent
from app.tools.schemas import ToolCall

logger = logging.getLogger("myoneAI.ai.manager")

# Confirmation keywords
CONFIRM_POSITIVE_PATTERNS = re.compile(
    r"(?i)\b(?:yes|confirm|proceed|sure|ok|okay|do it|continue|go ahead)\b|ஆம்|சரி|செய்|உறுதிப்படுத்துகிறேன்|கண்டிப்பா"
)
CONFIRM_NEGATIVE_PATTERNS = re.compile(
    r"(?i)\b(?:no|cancel|stop|abort|don'?t|nevermind)\b|வேண்டாம்|நிறுத்து|இல்லை|ரத்து"
)


class ConversationManager:
    """Manages short-term conversation history, prompt construction, memory injection, tools, and AI responses."""

    def __init__(
        self,
        provider: Optional[BaseAIProvider] = None,
        memory: Optional[MemoryManager] = None,
        tools: Optional[ToolExecutor] = None,
        permissions: Optional[PermissionManager] = None,
        max_history_messages: Optional[int] = None,
        system_prompt: Optional[str] = None,
        request_config: Optional[AIRequestConfig] = None,
    ) -> None:
        settings = get_settings()
        self.provider = provider or get_ai_provider()
        self.memory = memory or memory_manager
        self.permissions = permissions or permission_manager
        self.tools = tools or ToolExecutor(permissions=self.permissions)
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
            settings = get_settings()

            # 1. Handle Pending Confirmation if active
            pending = self.permissions.get_pending_confirmation() if self.permissions else None
            if pending and not pending.is_expired():
                if CONFIRM_POSITIVE_PATTERNS.search(clean_prompt):
                    consumed = self.permissions.consume_confirmation(pending.token)
                    if consumed:
                        tool_call = ToolCall(tool=consumed.tool_name, arguments=consumed.arguments)
                        tool_res = await self.tools.execute(tool_call, confirmed=True)
                        reply = tool_res.message

                        user_msg = ChatMessage(role="user", content=clean_prompt)
                        assistant_msg = ChatMessage(role="assistant", content=reply)
                        self._history.append(user_msg)
                        self._history.append(assistant_msg)
                        self._trim_history()

                        event_bus.emit(AIEvent.USER_MESSAGE, {"text": clean_prompt})
                        event_bus.emit(AIEvent.AI_RESPONSE, {"text": reply, "provider": "tool_executor"})
                        return reply

                elif CONFIRM_NEGATIVE_PATTERNS.search(clean_prompt):
                    self.permissions.cancel_all_confirmations()
                    reply = "Action cancelled. செயல் ரத்து செய்யப்பட்டது."
                    user_msg = ChatMessage(role="user", content=clean_prompt)
                    assistant_msg = ChatMessage(role="assistant", content=reply)
                    self._history.append(user_msg)
                    self._history.append(assistant_msg)
                    self._trim_history()

                    event_bus.emit(AIEvent.USER_MESSAGE, {"text": clean_prompt})
                    event_bus.emit(AIEvent.AI_RESPONSE, {"text": reply, "provider": "permission_manager"})
                    return reply

            # 2. Process Tools intent if tools are enabled
            if settings.tools_enabled and self.tools:
                tool_call = parse_tool_intent(clean_prompt)
                if tool_call:
                    try:
                        tool_res = await self.tools.execute(tool_call)
                        reply = tool_res.message
                        user_msg = ChatMessage(role="user", content=clean_prompt)
                        assistant_msg = ChatMessage(role="assistant", content=reply)
                        self._history.append(user_msg)
                        self._history.append(assistant_msg)
                        self._trim_history()

                        event_bus.emit(AIEvent.USER_MESSAGE, {"text": clean_prompt})
                        event_bus.emit(AIEvent.AI_RESPONSE, {"text": reply, "provider": "tool_executor"})
                        return reply
                    except Exception as tool_err:
                        logger.warning("Error running tool: %s", tool_err)

            # 3. Process explicit memory commands if memory system is enabled
            if settings.memory_enabled and self.memory:
                try:
                    memory_reply = await self.memory.process_memory_command(clean_prompt)
                    if memory_reply:
                        user_msg = ChatMessage(role="user", content=clean_prompt)
                        assistant_msg = ChatMessage(role="assistant", content=memory_reply)
                        self._history.append(user_msg)
                        self._history.append(assistant_msg)
                        self._trim_history()
                        event_bus.emit(AIEvent.USER_MESSAGE, {"text": clean_prompt})
                        event_bus.emit(AIEvent.AI_RESPONSE, {"text": memory_reply, "provider": "memory_engine"})
                        return memory_reply
                except Exception as mem_err:
                    logger.warning("Error processing memory command: %s", mem_err)

            # 4. Append user message to short-term history
            user_msg = ChatMessage(role="user", content=clean_prompt)
            self._history.append(user_msg)
            self._trim_history()

            event_bus.emit(AIEvent.USER_MESSAGE, {"text": clean_prompt})

            # 5. Build relevant memory context prompt
            effective_system_prompt = self.system_prompt
            if settings.memory_enabled and self.memory:
                memory_ctx = self.memory.get_context_for_prompt(clean_prompt)
                if memory_ctx:
                    effective_system_prompt = f"{self.system_prompt}\n{memory_ctx}"

            # 6. Build payload for provider
            messages_payload = [m.to_dict() for m in self._history]

            logger.info("Generating AI reply (Context size: %d messages)...", len(messages_payload))

            # 7. Call AI provider
            try:
                ai_resp = await self.provider.generate(
                    messages=messages_payload,
                    system_prompt=effective_system_prompt,
                    config=self.request_config,
                )
            except Exception as exc:
                logger.error("AI generation failed: %s", exc)
                # Remove the user message if provider failed so context isn't polluted
                if self._history and self._history[-1] is user_msg:
                    self._history.pop()
                raise

            # 8. Validate response
            reply_text = ai_resp.content.strip()
            if not reply_text:
                if self._history and self._history[-1] is user_msg:
                    self._history.pop()
                raise AIResponseError("AI provider returned blank response.")

            # 9. Append assistant turn
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
