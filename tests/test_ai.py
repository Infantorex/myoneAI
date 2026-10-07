"""Unit tests for AI Conversation Engine (app/ai/).

All tests use Mock providers or mocked HTTP clients with ZERO real API calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

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
from app.ai.manager import ConversationManager
from app.ai.models import AIRequestConfig, AIResponse, ChatMessage
from app.ai.prompts import SYSTEM_PROMPT_TAMIL_JARVIS
from app.ai.provider import (
    BaseAIProvider,
    GeminiAIProvider,
    MockAIProvider,
    OpenAICompatibleAIProvider,
    get_ai_provider,
)


# 1. Provider Selection & Factory
def test_get_ai_provider_factory():
    """Verify factory returns appropriate provider instance."""
    mock_prov = get_ai_provider("mock")
    assert isinstance(mock_prov, MockAIProvider)

    gemini_prov = get_ai_provider("gemini")
    assert isinstance(gemini_prov, GeminiAIProvider)

    openai_prov = get_ai_provider("openai")
    assert isinstance(openai_prov, OpenAICompatibleAIProvider)

    with pytest.raises(AIConfigurationError, match="Unsupported AI provider"):
        get_ai_provider("unsupported_llm_vendor")


# 2. Mock Provider Language & Intent Handling
@pytest.mark.asyncio
async def test_mock_provider_tamil_response():
    """Verify MockAIProvider handles Tamil input."""
    provider = MockAIProvider()
    resp = await provider.generate([{"role": "user", "content": "இன்று என்ன வேலை செய்யலாம்?"}])

    assert isinstance(resp, AIResponse)
    assert "project work" in resp.content or "வணக்கம்" in resp.content
    assert resp.provider == "mock"


@pytest.mark.asyncio
async def test_mock_provider_english_response():
    """Verify MockAIProvider handles English input."""
    provider = MockAIProvider()
    resp = await provider.generate([{"role": "user", "content": "Explain Python programming"}])

    assert "Python is an interpreted" in resp.content


@pytest.mark.asyncio
async def test_mock_provider_no_fake_action():
    """Verify MockAIProvider refuses fake PC control actions in Phase 4."""
    provider = MockAIProvider()
    resp = await provider.generate([{"role": "user", "content": "Open Chrome browser"}])

    assert "cannot open applications yet" in resp.content


# 3. ConversationManager Context & History Trimming
@pytest.mark.asyncio
async def test_conversation_manager_context_and_memory():
    """Verify multi-turn conversation maintains short-term context."""
    mock_prov = MockAIProvider()
    mgr = ConversationManager(provider=mock_prov, max_history_messages=6)

    # Turn 1
    r1 = await mgr.respond("My project is called Vibrawave")
    assert "Vibrawave" in r1
    assert mgr.history_length == 2  # 1 user + 1 assistant

    # Turn 2
    r2 = await mgr.respond("What should I improve in it?")
    assert mgr.history_length == 4

    history = mgr.get_history()
    assert history[0].role == "user"
    assert history[0].content == "My project is called Vibrawave"
    assert history[1].role == "assistant"
    assert history[2].role == "user"
    assert history[2].content == "What should I improve in it?"


@pytest.mark.asyncio
async def test_conversation_manager_history_limit():
    """Verify conversation history is bounded (FIFO trimming)."""
    mock_prov = MockAIProvider()
    mgr = ConversationManager(provider=mock_prov, max_history_messages=4)

    # Add 3 user-assistant pairs (6 messages)
    await mgr.respond("Msg 1")
    await mgr.respond("Msg 2")
    await mgr.respond("Msg 3")

    # Should be trimmed to max 4 messages
    assert mgr.history_length == 4
    history_texts = [m.content for m in mgr.get_history()]
    assert "Msg 1" not in history_texts
    assert "Msg 2" in history_texts
    assert "Msg 3" in history_texts


# 4. Input & Response Validation
@pytest.mark.asyncio
async def test_empty_prompt_error():
    """Verify empty or whitespace-only prompts raise EmptyPromptError."""
    mgr = ConversationManager(provider=MockTTSProvider() if False else MockAIProvider())

    with pytest.raises(EmptyPromptError):
        await mgr.respond("")

    with pytest.raises(EmptyPromptError):
        await mgr.respond("    \n\t  ")


@pytest.mark.asyncio
async def test_ai_response_blank_error():
    """Verify blank response from AI raises AIResponseError."""
    mock_prov = MockAIProvider(default_response="   ")
    mgr = ConversationManager(provider=mock_prov)

    with pytest.raises(AIResponseError):
        await mgr.respond("Hello")


# 5. Clear History
@pytest.mark.asyncio
async def test_clear_history():
    """Verify clear_history resets context."""
    mgr = ConversationManager(provider=MockAIProvider())
    await mgr.respond("Hello")
    assert mgr.history_length == 2

    mgr.clear_history()
    assert mgr.history_length == 0


# 6. Synchronous respond_sync Wrapper
def test_respond_sync_wrapper():
    """Verify synchronous wrapper executes cleanly."""
    mgr = ConversationManager(provider=MockAIProvider())
    reply = mgr.respond_sync("வணக்கம் Jarvis")
    assert "Infanto" in reply or len(reply) > 0


# 7. Gemini Provider Mocked HTTP Tests
@pytest.mark.asyncio
async def test_gemini_missing_api_key():
    """Verify GeminiAIProvider raises AIAuthenticationError when API key is missing."""
    prov = GeminiAIProvider(api_key=None)
    with pytest.raises(AIAuthenticationError):
        await prov.generate([{"role": "user", "content": "Hello"}])


@pytest.mark.asyncio
async def test_gemini_mocked_success():
    """Verify GeminiAIProvider processes response JSON correctly."""
    prov = GeminiAIProvider(api_key="AIzaSy_fake_test_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "வணக்கம்! நான் உங்கள் JARVIS assistant."}],
                    "role": "model",
                }
            }
        ],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 8},
    }

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
        res = await prov.generate(
            messages=[{"role": "user", "content": "வணக்கம்"}],
            system_prompt=SYSTEM_PROMPT_TAMIL_JARVIS,
        )
        assert res.content == "வணக்கம்! நான் உங்கள் JARVIS assistant."
        assert res.provider == "gemini"


@pytest.mark.asyncio
async def test_gemini_rate_limit_and_auth_error():
    """Verify Gemini error status codes raise structured exceptions."""
    prov = GeminiAIProvider(api_key="AIzaSy_fake_key")

    # 429 Rate Limit
    mock_429 = MagicMock(status_code=429, text="Quota exceeded")
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_429):
        with pytest.raises(AIRateLimitError):
            await prov.generate([{"role": "user", "content": "Hello"}])

    # 401 Auth error
    mock_401 = MagicMock(status_code=401, text="API key invalid")
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_401):
        with pytest.raises(AIAuthenticationError):
            await prov.generate([{"role": "user", "content": "Hello"}])


@pytest.mark.asyncio
async def test_gemini_timeout_error():
    """Verify Gemini request timeout raises AITimeoutError."""
    prov = GeminiAIProvider(api_key="AIzaSy_fake_key")

    with patch.object(httpx.AsyncClient, "post", side_effect=httpx.TimeoutException("Read timed out")):
        with pytest.raises(AITimeoutError):
            await prov.generate([{"role": "user", "content": "Hello"}])


# 8. OpenAI-Compatible Provider Mocked HTTP Tests
@pytest.mark.asyncio
async def test_openai_compatible_mocked_success():
    """Verify OpenAICompatibleAIProvider processes chat completion response."""
    prov = OpenAICompatibleAIProvider(api_key="sk-fake-openai-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Hello Infanto, system is ready.",
                }
            }
        ],
        "usage": {"total_tokens": 20},
    }

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
        res = await prov.generate([{"role": "user", "content": "Hello"}])
        assert res.content == "Hello Infanto, system is ready."
        assert res.provider == "openai-compatible"
