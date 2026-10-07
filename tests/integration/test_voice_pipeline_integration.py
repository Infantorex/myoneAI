"""Integration tests for the complete Voice Pipeline (VAD -> STT -> AI -> TTS)."""

import asyncio
import pytest

from app.ai.manager import ConversationManager
from app.ai.provider import MockAIProvider
from app.voice.audio import AudioPlayer
from app.voice.conversation import VoiceConversationManager
from app.voice.stt import MockSTTProvider
from app.voice.tts import MockTTSProvider
from app.voice.vad import VoiceActivityDetector
from tests.fixtures.audio_fixtures import generate_synthetic_pcm


@pytest.mark.asyncio
async def test_full_voice_turn_cycle():
    """Verify complete simulated turn from audio bytes to TTS synthesis."""
    stt = MockSTTProvider(default_response="வணக்கம் JARVIS")
    ai = ConversationManager(provider=MockAIProvider(default_response="வணக்கம் Infanto! எப்படி உதவ வேண்டும்?"))
    tts = MockTTSProvider()

    # 1. Simulate speech transcription
    raw_pcm = generate_synthetic_pcm(duration_sec=0.2)
    stt_res = await stt.transcribe(raw_pcm)
    assert stt_res.text == "வணக்கம் JARVIS"

    # 2. AI response
    ai_reply = await ai.respond(stt_res.text)
    assert "வணக்கம் Infanto" in ai_reply

    # 3. TTS generation
    tts_res = await tts.synthesize(ai_reply)
    assert len(tts_res.audio_bytes) > 0
