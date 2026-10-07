"""Reliability: Graceful Failure Recovery across Subsystems."""

import asyncio
import pytest

from app.ai.errors import AIProviderError
from app.ai.manager import ConversationManager
from app.ai.provider import MockAIProvider
from app.voice.exceptions import STTError, TTSError
from app.voice.stt import MockSTTProvider
from app.voice.tts import MockTTSProvider


@pytest.mark.asyncio
async def test_ai_provider_failure_recovery_leaves_history_clean():
    """Verify that when AI provider fails, unfulfilled user turn is pruned to prevent corrupt context."""
    provider = MockAIProvider()
    provider.should_fail = AIProviderError("Simulated cloud LLM outage")
    mgr = ConversationManager(provider=provider)

    with pytest.raises(AIProviderError):
        await mgr.respond("Hello JARVIS")

    # History must not contain dangling user message without assistant reply
    assert mgr.history_length == 0


@pytest.mark.asyncio
async def test_stt_provider_failure_handled_gracefully():
    """Verify STT provider raises structured STTError and does not crash process."""
    stt = MockSTTProvider()
    stt.should_fail = STTError("Simulated network timeout during speech recognition")

    with pytest.raises(STTError):
        await stt.transcribe(b"fake_audio_bytes")


@pytest.mark.asyncio
async def test_tts_provider_failure_handled_gracefully():
    """Verify TTS provider raises structured TTSError on synthesis failure."""
    tts = MockTTSProvider()
    tts.should_fail = TTSError("Simulated audio decoder failure")

    with pytest.raises(TTSError):
        await tts.synthesize("Test speech text")
