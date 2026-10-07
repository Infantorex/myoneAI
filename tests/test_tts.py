"""Unit tests for Text-to-Speech subsystem (app/voice/tts.py).

All tests use mocked providers and local fixtures with ZERO real cloud API calls.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.events import VoiceEvent, event_bus
from app.voice.audio import AudioPlayer
from app.voice.exceptions import (
    EmptyTextError,
    TextTooLongError,
    TTSConfigurationError,
    TTSError,
    TTSProviderError,
    TTSTimeoutError,
)
from app.voice.tts import (
    BaseTTS,
    EdgeTTSProvider,
    MockTTSProvider,
    TTSManager,
    TTSResult,
    format_rate_param,
    format_volume_param,
    get_tts_provider,
)


# 1. Parameter Formatting Tests
def test_format_rate_and_volume_params():
    """Verify rate and volume parameter conversion for edge-tts."""
    assert format_rate_param(1.0) == "+0%"
    assert format_rate_param(1.2) == "+20%"
    assert format_rate_param(0.8) == "-20%"
    assert format_rate_param("+15%") == "+15%"
    assert format_rate_param(None) == "+0%"

    assert format_volume_param(1.0) == "+0%"
    assert format_volume_param(1.5) == "+50%"
    assert format_volume_param(0.5) == "-50%"
    assert format_volume_param(None) == "+0%"


# 2. Mock TTS Provider Tests (Tamil, English, Mixed)
@pytest.mark.asyncio
async def test_mock_tts_tamil_synthesis():
    """Verify MockTTSProvider synthesizes Tamil text."""
    provider = MockTTSProvider()
    result = await provider.synthesize("வணக்கம் Infanto, எப்படி இருக்கிறீர்கள்?", voice="ta-IN-PallaviNeural")

    assert isinstance(result, TTSResult)
    assert result.text == "வணக்கம் Infanto, எப்படி இருக்கிறீர்கள்?"
    assert result.voice == "ta-IN-PallaviNeural"
    assert result.format == "wav"
    assert len(result.audio_bytes) > 0
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_mock_tts_english_and_mixed():
    """Verify MockTTSProvider handles English and Mixed language text."""
    provider = MockTTSProvider()

    res_en = await provider.synthesize("Hello Infanto, system is ready.")
    assert res_en.text == "Hello Infanto, system is ready."

    res_mix = await provider.synthesize("வணக்கம், இன்று Python project work பண்ணலாமா?")
    assert res_mix.text == "வணக்கம், இன்று Python project work பண்ணலாமா?"


@pytest.mark.asyncio
async def test_mock_tts_empty_text_error():
    """Verify empty text raises EmptyTextError."""
    provider = MockTTSProvider()
    with pytest.raises(EmptyTextError):
        await provider.synthesize("")

    with pytest.raises(EmptyTextError):
        await provider.synthesize("   \n\t  ")


# 3. TTS Provider Factory & Config
def test_get_tts_provider_factory():
    """Verify factory returns appropriate provider."""
    edge = get_tts_provider("edge-tts")
    assert isinstance(edge, EdgeTTSProvider)

    mock = get_tts_provider("mock")
    assert isinstance(mock, MockTTSProvider)

    with pytest.raises(TTSConfigurationError):
        get_tts_provider("unknown_tts_provider_123")


# 4. EdgeTTS Provider Mocked Tests
@pytest.mark.asyncio
async def test_edge_tts_mocked_success():
    """Verify EdgeTTSProvider streaming synthesis with mocked Communicate."""
    provider = EdgeTTSProvider(default_voice="ta-IN-PallaviNeural")

    mock_chunks = [
        {"type": "audio", "data": b"CHUNK_1_BYTES_DATA"},
        {"type": "audio", "data": b"_CHUNK_2_BYTES_DATA"},
        {"type": "metadata", "data": {}},
    ]

    async def mock_stream():
        for chunk in mock_chunks:
            yield chunk

    mock_comm = MagicMock()
    mock_comm.stream = mock_stream

    with patch("edge_tts.Communicate", return_value=mock_comm):
        result = await provider.synthesize("வணக்கம் Infanto", voice="ta-IN-ValluvarNeural", rate=1.1)
        assert result.audio_bytes == b"CHUNK_1_BYTES_DATA_CHUNK_2_BYTES_DATA"
        assert result.voice == "ta-IN-ValluvarNeural"
        assert result.format == "mp3"


@pytest.mark.asyncio
async def test_edge_tts_mocked_failure():
    """Verify EdgeTTS handles synthesis exceptions."""
    provider = EdgeTTSProvider()

    with patch("edge_tts.Communicate", side_effect=RuntimeError("Network socket closed")):
        with pytest.raises(TTSProviderError):
            await provider.synthesize("Test text")


# 5. TTSManager Text Sanitization & Chunking
def test_tts_manager_sanitize_text():
    """Verify text normalization and length validation."""
    mgr = TTSManager(provider=MockTTSProvider(), max_text_length=100)

    # Clean whitespace
    cleaned = mgr.sanitize_text("  வணக்கம்   \n\t Infanto   ")
    assert cleaned == "வணக்கம் Infanto"

    # Empty text rejection
    with pytest.raises(EmptyTextError):
        mgr.sanitize_text("")

    with pytest.raises(EmptyTextError):
        mgr.sanitize_text("    ")

    # Long text rejection
    with pytest.raises(TextTooLongError):
        mgr.sanitize_text("அ" * 150)


# 6. TTSManager Overlapping Speech Prevention & Event Emission
@pytest.mark.asyncio
async def test_tts_manager_speak_and_overlap_prevention():
    """Verify TTSManager stops prior speech and emits events."""
    mock_provider = MockTTSProvider()
    mock_player = MagicMock(spec=AudioPlayer)
    mock_player.is_playing = False
    mock_player.play_async = AsyncMock()
    mock_player.stop = MagicMock()

    mgr = TTSManager(provider=mock_provider, player=mock_player)

    events_received = []

    def on_tts_event(evt):
        events_received.append(evt.name)

    event_bus.subscribe(VoiceEvent.TTS_STARTED, on_tts_event)
    event_bus.subscribe(VoiceEvent.TTS_FINISHED, on_tts_event)

    try:
        # First speak call
        result = await mgr.speak("வணக்கம் Infanto", wait=True)
        assert result.text == "வணக்கம் Infanto"
        assert mock_player.play_async.called

        # Verify events emitted
        assert VoiceEvent.TTS_STARTED.value in events_received
        assert VoiceEvent.TTS_FINISHED.value in events_received

        # Simulate ongoing playback when second speak is called
        mock_player.is_playing = True
        await mgr.speak("இரண்டாவது செய்தி")
        # Ensure player.stop() was invoked to prevent overlap
        assert mock_player.stop.called

    finally:
        event_bus.unsubscribe(VoiceEvent.TTS_STARTED, on_tts_event)
        event_bus.unsubscribe(VoiceEvent.TTS_FINISHED, on_tts_event)


# 7. Synchronous Speak Wrapper
def test_tts_manager_speak_sync():
    """Verify speak_sync executes without event loop errors."""
    mock_provider = MockTTSProvider()
    mock_player = MagicMock(spec=AudioPlayer)
    mock_player.play_async = AsyncMock()
    mock_player.is_playing = False

    mgr = TTSManager(provider=mock_provider, player=mock_player)
    result = mgr.speak_sync("Synchronous test")
    assert result.text == "Synchronous test"
