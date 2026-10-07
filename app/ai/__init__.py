"""AI Reasoning, conversation manager, persona prompts, and cloud LLM provider subsystem.
"""

from app.ai.errors import (
    AIAuthenticationError,
    AIConfigurationError,
    AIError,
    AIProviderError,
    AIRateLimitError,
    AIResponseError,
    AITimeoutError,
    EmptyPromptError,
)
from app.ai.manager import ConversationManager, conversation_manager
from app.ai.models import AIRequestConfig, AIResponse, ChatMessage
from app.ai.prompts import SYSTEM_PROMPT_TAMIL_JARVIS
from app.ai.provider import (
    BaseAIProvider,
    GeminiAIProvider,
    MockAIProvider,
    OpenAICompatibleAIProvider,
    get_ai_provider,
)

__all__ = [
    "AIError",
    "AIProviderError",
    "AIAuthenticationError",
    "AITimeoutError",
    "AIRateLimitError",
    "AIResponseError",
    "AIConfigurationError",
    "EmptyPromptError",
    "ChatMessage",
    "AIRequestConfig",
    "AIResponse",
    "SYSTEM_PROMPT_TAMIL_JARVIS",
    "BaseAIProvider",
    "GeminiAIProvider",
    "OpenAICompatibleAIProvider",
    "MockAIProvider",
    "get_ai_provider",
    "ConversationManager",
    "conversation_manager",
]
