"""Provider-independent AI inference interfaces and cloud implementations.

Decouples the assistant from any specific AI vendor (Gemini, OpenAI, Groq, OpenRouter).
Uses lightweight async HTTP requests with zero heavy local model weights.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import httpx

from app.ai.errors import (
    AIAuthenticationError,
    AIConfigurationError,
    AIError,
    AIProviderError,
    AIRateLimitError,
    AIResponseError,
    AITimeoutError,
)
from app.ai.models import AIRequestConfig, AIResponse
from app.core.config import get_settings

logger = logging.getLogger("myoneAI.ai.provider")


class BaseAIProvider(ABC):
    """Abstract base class for all AI inference providers."""

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        config: Optional[AIRequestConfig] = None,
    ) -> AIResponse:
        """Send chat messages to cloud AI and receive generated response.

        Args:
            messages: List of message dictionaries with 'role' ('user'/'assistant') and 'content'.
            system_prompt: Persona and behavioral instructions.
            config: Inference configuration (temperature, max tokens, timeout).

        Returns:
            AIResponse object containing the generated content string.
        """
        pass

    def generate_sync(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        config: Optional[AIRequestConfig] = None,
    ) -> AIResponse:
        """Synchronous wrapper for AI generation."""
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, self.generate(messages, system_prompt, config))
                return future.result()
        except RuntimeError:
            return asyncio.run(self.generate(messages, system_prompt, config))


class GeminiAIProvider(BaseAIProvider):
    """Google Gemini cloud API provider via lightweight REST."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-1.5-flash",
        timeout_sec: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_sec = timeout_sec

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        config: Optional[AIRequestConfig] = None,
    ) -> AIResponse:
        if not self.api_key or not self.api_key.strip() or self.api_key.startswith("your_"):
            raise AIAuthenticationError("Gemini API key is not configured. Please set AI_API_KEY in .env.")

        start_time = time.time()
        req_config = config or AIRequestConfig(timeout_sec=self.timeout_sec)

        # Convert messages to Gemini contents format
        contents = []
        for msg in messages:
            role = "model" if msg.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": req_config.temperature,
                "maxOutputTokens": req_config.max_output_tokens,
            },
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}],
            }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=req_config.timeout_sec) as client:
                response = await client.post(url, json=payload)

            if response.status_code in (401, 403):
                raise AIAuthenticationError(f"Gemini API authentication failed: HTTP {response.status_code}")
            elif response.status_code == 429:
                raise AIRateLimitError("Gemini API rate limit / quota exceeded.")
            elif response.status_code != 200:
                raise AIProviderError(f"Gemini API returned error HTTP {response.status_code}: {response.text}")

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise AIResponseError("Gemini returned empty candidate response.")

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts or "text" not in parts[0]:
                raise AIResponseError("Gemini response did not contain text content.")

            text_response = parts[0]["text"].strip()
            if not text_response:
                raise AIResponseError("Gemini returned blank text content.")

            elapsed = time.time() - start_time
            logger.info("Gemini generated %d chars in %.2fs [%s]", len(text_response), elapsed, self.model)

            return AIResponse(
                content=text_response,
                provider="gemini",
                model=self.model,
                duration_sec=round(elapsed, 2),
                usage=data.get("usageMetadata"),
            )

        except (AIAuthenticationError, AIRateLimitError, AIProviderError, AIResponseError):
            raise
        except httpx.TimeoutException as t_err:
            raise AITimeoutError(f"Gemini request timed out after {req_config.timeout_sec}s: {t_err}") from t_err
        except Exception as exc:
            raise AIProviderError(f"Gemini request failed: {exc}") from exc


class OpenAICompatibleAIProvider(BaseAIProvider):
    """OpenAI-compatible cloud API provider (OpenAI, Groq, OpenRouter, etc.)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
        timeout_sec: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.timeout_sec = timeout_sec

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        config: Optional[AIRequestConfig] = None,
    ) -> AIResponse:
        if not self.api_key or not self.api_key.strip():
            raise AIAuthenticationError("OpenAI-compatible API key is not configured.")

        start_time = time.time()
        req_config = config or AIRequestConfig(timeout_sec=self.timeout_sec)

        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        payload_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": req_config.temperature,
            "max_tokens": req_config.max_output_tokens,
        }

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=req_config.timeout_sec) as client:
                response = await client.post(url, headers=headers, json=payload)

            if response.status_code in (401, 403):
                raise AIAuthenticationError("API authentication failed.")
            elif response.status_code == 429:
                raise AIRateLimitError("API rate limit exceeded.")
            elif response.status_code != 200:
                raise AIProviderError(f"API returned error HTTP {response.status_code}: {response.text}")

            data = response.json()
            choices = data.get("choices", [])
            if not choices or "message" not in choices[0]:
                raise AIResponseError("Malformed response structure from AI provider.")

            text_response = choices[0]["message"].get("content", "").strip()
            if not text_response:
                raise AIResponseError("AI provider returned empty message content.")

            elapsed = time.time() - start_time
            return AIResponse(
                content=text_response,
                provider="openai-compatible",
                model=self.model,
                duration_sec=round(elapsed, 2),
                usage=data.get("usage"),
            )

        except (AIAuthenticationError, AIRateLimitError, AIProviderError, AIResponseError):
            raise
        except httpx.TimeoutException as t_err:
            raise AITimeoutError(f"AI request timed out: {t_err}") from t_err
        except Exception as exc:
            raise AIProviderError(f"AI request failed: {exc}") from exc


class MockAIProvider(BaseAIProvider):
    """Deterministic mock provider for offline testing and CI/CD without network."""

    def __init__(self, default_response: str = "வணக்கம் Infanto! எப்படி இருக்கிறீர்கள்?") -> None:
        self.default_response = default_response
        self.call_count = 0
        self.last_messages: List[Dict[str, str]] = []
        self.should_fail: Optional[Exception] = None

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        config: Optional[AIRequestConfig] = None,
    ) -> AIResponse:
        self.call_count += 1
        self.last_messages = list(messages)

        if self.should_fail:
            raise self.should_fail

        last_user_msg = next(
            (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
            "",
        ).lower()

        # Dynamic mock response matching language/intent
        if "recursion" in last_user_msg or "explain" in last_user_msg or "python" in last_user_msg:
            reply = "Python is an interpreted, high-level programming language known for readable syntax."
        elif "vibrawave" in last_user_msg:
            reply = "Vibrawave sounds like an awesome project! We can focus on low-latency audio processing."
        elif "chrome" in last_user_msg or "open app" in last_user_msg:
            reply = "I cannot open applications yet. PC automation tools will be enabled in a future phase."
        elif any(w in last_user_msg for w in ["இன்று", "வேலை", "பண்ணலாம்", "என்ன"]):
            reply = "இன்று project work, coding அல்லது உங்கள் pending tasksல ஒன்றை முடிக்கலாம். எதை start பண்ணலாம்?"
        else:
            reply = self.default_response

        return AIResponse(
            content=reply,
            provider="mock",
            model="mock-v1",
            duration_sec=0.01,
        )


def get_ai_provider(provider_name: Optional[str] = None) -> BaseAIProvider:
    """Factory to instantiate the configured AI provider."""
    settings = get_settings()
    name = (provider_name or settings.ai_provider).lower()

    if name in ("gemini", "google"):
        return GeminiAIProvider(
            api_key=settings.ai_api_key,
            model=settings.ai_model,
            timeout_sec=settings.ai_timeout,
        )
    elif name in ("openai", "groq", "openrouter", "ollama-remote"):
        return OpenAICompatibleAIProvider(
            api_key=settings.ai_api_key,
            model=settings.ai_model,
            base_url=settings.ai_base_url,
            timeout_sec=settings.ai_timeout,
        )
    elif name == "mock":
        return MockAIProvider()
    else:
        raise AIConfigurationError(
            f"Unsupported AI provider: '{name}'. Supported providers: 'gemini', 'openai', 'groq', 'mock'."
        )
