"""Unit and integration tests for Natural Voice Conversation Loop (app/voice/conversation.py).

All tests use Mock providers and synthetic fixtures with ZERO real API or hardware calls.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.ai.errors import AIError, AIProviderError
from app.ai.manager import ConversationManager
from app.ai.models import AIResponse
from app.ai.provider import MockAIProvider
from app.core.events import VoiceEvent, event_bus
from app.core.state import AssistantState, state_manager
from app.voice.audio_config import DEFAULT_AUDIO_CONFIG
from app.voice.conversation import VoiceConversationManager, VoiceLoopState
from app.voice.exceptions import (
    MicrophoneError,
    NoSpeechDetectedError,
    STTError,
    STTProviderError,
    TTSError,
    TTSProviderError,
)
from app.voice.microphone import MicrophoneManager, pcm_to_wav_bytes
from app.voice.stt import MockSTTProvider, STTResult
from app.voice.tts import MockTTSProvider, TTSManager, TTSResult


@pytest.fixture
def sample_wav_audio() -> bytes:
    """Generate 0.2s 16kHz mono WAV bytes for test input."""
    pcm = b"\x00\x00" * 3200
    return pcm_to_wav_bytes(pcm, DEFAULT_AUDIO_CONFIG)


# 1. Full Successful End-to-End Voice Cycle Test
@pytest.mark.asyncio
async def test_successful_voice_conversation_cycle(sample_wav_audio):
    """Verify complete pipeline: Mic -> STT -> AI -> TTS -> Speaker -> IDLE."""
    mock_mic = MagicMock(spec=MicrophoneManager)
    mock_mic.record_phrase.return_value = sample_wav_audio
    mock_mic.is_recording = False

    mock_stt = MockSTTProvider(default_response="வணக்கம் Jarvis")
    mock_ai_prov = MockAIProvider(default_response="வணக்கம் Infanto! இன்று என்ன வேலை செய்யலாம்?")
    ai_mgr = ConversationManager(provider=mock_ai_prov)

    mock_tts_prov = MockTTSProvider()
    tts_mgr = TTSManager(provider=mock_tts_prov)
    # Mock actual audio output device
    tts_mgr.player.play_async = AsyncMock()

    voice_mgr = VoiceConversationManager(
        microphone=mock_mic,
        stt=mock_stt,
        ai=ai_mgr,
        tts=tts_mgr,
        language="ta-IN",
    )

    # Initial state check
    assert voice_mgr.current_state == VoiceLoopState.IDLE

    # Run single turn
    turn_result = await voice_mgr.run_once()

    assert turn_result is not None
    assert turn_result["transcript"] == "வணக்கம் Jarvis"
    assert turn_result["response"] == "வணக்கம் Infanto! இன்று என்ன வேலை செய்யலாம்?"
    assert turn_result["stt_duration"] >= 0.0
    assert turn_result["ai_duration"] >= 0.0
    assert turn_result["total_duration"] >= 0.0

    # Verify state returned cleanly to IDLE
    assert voice_mgr.current_state == VoiceLoopState.IDLE
    assert state_manager.current_state == AssistantState.IDLE


# 2. State Transitions Verification
@pytest.mark.asyncio
async def test_state_transitions_sequence(sample_wav_audio):
    """Verify state transitions: IDLE -> LISTENING -> PROCESSING_SPEECH -> THINKING -> SPEAKING -> IDLE."""
    mock_mic = MagicMock(spec=MicrophoneManager)
    mock_mic.record_phrase.return_value = sample_wav_audio

    mock_stt = MockSTTProvider(default_response="Test speech")
    mock_ai_prov = MockAIProvider(default_response="Test response")
    ai_mgr = ConversationManager(provider=mock_ai_prov)

    mock_tts_prov = MockTTSProvider()
    tts_mgr = TTSManager(provider=mock_tts_prov)
    tts_mgr.player.play_async = AsyncMock()

    voice_mgr = VoiceConversationManager(
        microphone=mock_mic,
        stt=mock_stt,
        ai=ai_mgr,
        tts=tts_mgr,
    )

    states_visited = []

    # Monitor state changes
    def state_tracker(evt):
        states_visited.append(evt.data.get("new_state"))

    event_bus.subscribe("system.state_changed", state_tracker)

    try:
        await voice_mgr.run_once()
        assert AssistantState.LISTENING.value in states_visited
        assert AssistantState.PROCESSING.value in states_visited
        assert AssistantState.SPEAKING.value in states_visited
        assert voice_mgr.current_state == VoiceLoopState.IDLE
    finally:
        event_bus.unsubscribe("system.state_changed", state_tracker)


# 3. Silence / No Speech Detected Recovery
@pytest.mark.asyncio
async def test_no_speech_detected_recovery():
    """Verify silence gracefully returns None and resets state to IDLE without crash."""
    mock_mic = MagicMock(spec=MicrophoneManager)
    mock_mic.record_phrase.side_effect = NoSpeechDetectedError("Silence")

    voice_mgr = VoiceConversationManager(
        microphone=mock_mic,
        stt=MockSTTProvider(),
        ai=ConversationManager(provider=MockAIProvider()),
        tts=TTSManager(provider=MockTTSProvider()),
    )

    result = await voice_mgr.run_once()
    assert result is None
    assert voice_mgr.current_state == VoiceLoopState.IDLE


# 4. STT Failure Recovery
@pytest.mark.asyncio
async def test_stt_failure_recovery(sample_wav_audio):
    """Verify STT provider failure recovers gracefully to IDLE."""
    mock_mic = MagicMock(spec=MicrophoneManager)
    mock_mic.record_phrase.return_value = sample_wav_audio

    mock_stt = MockSTTProvider()
    mock_stt.should_fail = STTProviderError("STT cloud service down")

    voice_mgr = VoiceConversationManager(
        microphone=mock_mic,
        stt=mock_stt,
        ai=ConversationManager(provider=MockAIProvider()),
        tts=TTSManager(provider=MockTTSProvider()),
    )

    result = await voice_mgr.run_once()
    assert result is None
    assert voice_mgr.current_state == VoiceLoopState.IDLE


# 5. AI Reasoning Failure Recovery
@pytest.mark.asyncio
async def test_ai_failure_recovery(sample_wav_audio):
    """Verify AI provider failure speaks error message and resets to IDLE."""
    mock_mic = MagicMock(spec=MicrophoneManager)
    mock_mic.record_phrase.return_value = sample_wav_audio

    mock_ai_prov = MockAIProvider()
    mock_ai_prov.should_fail = AIProviderError("AI quota exceeded")
    ai_mgr = ConversationManager(provider=mock_ai_prov)

    mock_tts_prov = MockTTSProvider()
    tts_mgr = TTSManager(provider=mock_tts_prov)
    tts_mgr.player.play_async = AsyncMock()

    voice_mgr = VoiceConversationManager(
        microphone=mock_mic,
        stt=MockSTTProvider(default_response="Hello"),
        ai=ai_mgr,
        tts=tts_mgr,
    )

    result = await voice_mgr.run_once()
    assert result is None
    assert voice_mgr.current_state == VoiceLoopState.IDLE


# 6. TTS Output Failure Recovery
@pytest.mark.asyncio
async def test_tts_failure_recovery(sample_wav_audio):
    """Verify TTS failure does not crash the loop and resets to IDLE."""
    mock_mic = MagicMock(spec=MicrophoneManager)
    mock_mic.record_phrase.return_value = sample_wav_audio

    mock_tts_prov = MockTTSProvider()
    mock_tts_prov.should_fail = TTSProviderError("Speaker driver busy")
    tts_mgr = TTSManager(provider=mock_tts_prov)

    voice_mgr = VoiceConversationManager(
        microphone=mock_mic,
        stt=MockSTTProvider(default_response="Hello"),
        ai=ConversationManager(provider=MockAIProvider()),
        tts=tts_mgr,
    )

    result = await voice_mgr.run_once()
    assert result is not None
    assert result["transcript"] == "Hello"
    assert voice_mgr.current_state == VoiceLoopState.IDLE


# 7. Context Preservation Across Turns
@pytest.mark.asyncio
async def test_voice_loop_context_preservation(sample_wav_audio):
    """Verify multi-turn voice conversations maintain conversation history."""
    mock_mic = MagicMock(spec=MicrophoneManager)
    mock_mic.record_phrase.return_value = sample_wav_audio

    mock_stt = MockSTTProvider()
    mock_ai_prov = MockAIProvider()
    ai_mgr = ConversationManager(provider=mock_ai_prov, max_history_messages=10)

    mock_tts_prov = MockTTSProvider()
    tts_mgr = TTSManager(provider=mock_tts_prov)
    tts_mgr.player.play_async = AsyncMock()

    voice_mgr = VoiceConversationManager(
        microphone=mock_mic,
        stt=mock_stt,
        ai=ai_mgr,
        tts=tts_mgr,
    )

    # Turn 1
    mock_stt.default_response = "My project is Vibrawave"
    await voice_mgr.run_once()
    assert ai_mgr.history_length == 2

    # Turn 2
    mock_stt.default_response = "What should I improve in it?"
    await voice_mgr.run_once()
    assert ai_mgr.history_length == 4

    history = ai_mgr.get_history()
    assert history[0].content == "My project is Vibrawave"
    assert history[2].content == "What should I improve in it?"


# 8. Interactive Loop Exit on Speech Command
@pytest.mark.asyncio
async def test_interactive_loop_exit_command(sample_wav_audio):
    """Verify interactive loop terminates when exit command is recognized."""
    mock_mic = MagicMock(spec=MicrophoneManager)
    mock_mic.record_phrase.return_value = sample_wav_audio

    mock_stt = MockSTTProvider(default_response="exit")
    voice_mgr = VoiceConversationManager(
        microphone=mock_mic,
        stt=mock_stt,
        ai=ConversationManager(provider=MockAIProvider()),
        tts=TTSManager(provider=MockTTSProvider()),
    )
    voice_mgr.tts.player.play_async = AsyncMock()

    turns_recorded = []
    # Should run 1 turn, see 'exit', and break
    await voice_mgr.run_interactive(on_turn=lambda t: turns_recorded.append(t))

    assert len(turns_recorded) == 1
    assert turns_recorded[0]["transcript"] == "exit"
    assert voice_mgr.current_state == VoiceLoopState.IDLE


# 9. Stop & Cancellation Handling
@pytest.mark.asyncio
async def test_voice_loop_stop():
    """Verify stop() interrupts active session cleanly."""
    mock_mic = MagicMock(spec=MicrophoneManager)
    mock_mic.is_recording = True

    mock_tts = MagicMock(spec=TTSManager)

    voice_mgr = VoiceConversationManager(
        microphone=mock_mic,
        stt=MockSTTProvider(),
        ai=ConversationManager(provider=MockAIProvider()),
        tts=mock_tts,
    )

    voice_mgr.stop()
    assert mock_mic.stop_recording.called
    assert mock_tts.stop.called
    assert voice_mgr.current_state == VoiceLoopState.IDLE
