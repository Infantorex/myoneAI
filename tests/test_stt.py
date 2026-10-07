"""Unit tests for Speech-to-Text providers and interfaces (app/voice/stt.py).
"""

import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import speech_recognition as sr
import httpx

from app.voice.audio_config import AudioConfig, DEFAULT_AUDIO_CONFIG
from app.voice.exceptions import (
    InvalidAudioError,
    NoSpeechDetectedError,
    STTAuthenticationError,
    STTError,
    STTProviderError,
    STTRateLimitError,
    STTTimeoutError,
)
from app.voice.microphone import pcm_to_wav_bytes
from app.voice.stt import (
    BaseSTT,
    GoogleSTTProvider,
    GroqWhisperSTTProvider,
    MockSTTProvider,
    STTResult,
    get_stt_provider,
)


@pytest.fixture
def sample_wav_bytes() -> bytes:
    """Generate minimal valid 16kHz mono WAV bytes for testing."""
    # 0.5s of 16kHz 16-bit PCM (silence or small signal)
    pcm = b"\x00\x00" * 8000
    return pcm_to_wav_bytes(pcm, DEFAULT_AUDIO_CONFIG)


# 1. Test Base Interface & Mock Provider
@pytest.mark.asyncio
async def test_mock_stt_tamil_response(sample_wav_bytes):
    """Verify MockSTTProvider returns Tamil text accurately."""
    provider = MockSTTProvider(default_response="ஜார்விஸ், இன்று என்ன வேலை இருக்கு?")
    result = await provider.transcribe(sample_wav_bytes, language="ta-IN")

    assert isinstance(result, STTResult)
    assert result.text == "ஜார்விஸ், இன்று என்ன வேலை இருக்கு?"
    assert result.language == "ta-IN"
    assert result.provider == "mock"
    assert result.confidence == 1.0


@pytest.mark.asyncio
async def test_mock_stt_english_response(sample_wav_bytes):
    """Verify English transcription response."""
    provider = MockSTTProvider(default_response="What is the battery percentage?")
    result = await provider.transcribe(sample_wav_bytes, language="en-US")

    assert result.text == "What is the battery percentage?"
    assert result.language == "en-US"


@pytest.mark.asyncio
async def test_mock_stt_mixed_speech_response(sample_wav_bytes):
    """Verify Tamil + English mixed speech response."""
    provider = MockSTTProvider(default_response="Open Chrome பண்ணு")
    result = await provider.transcribe(sample_wav_bytes, language="ta-IN")

    assert result.text == "Open Chrome பண்ணு"


# 2. Test Factory & Invalid Provider
def test_get_stt_provider_factory():
    """Verify factory returns appropriate provider instance."""
    google = get_stt_provider("google")
    assert isinstance(google, GoogleSTTProvider)

    groq = get_stt_provider("groq")
    assert isinstance(groq, GroqWhisperSTTProvider)

    mock = get_stt_provider("mock")
    assert isinstance(mock, MockSTTProvider)

    with pytest.raises(ValueError, match="Unsupported STT provider"):
        get_stt_provider("unsupported_provider_xyz")


# 3. Test Invalid & Empty Audio Handling
@pytest.mark.asyncio
async def test_empty_audio_raises_error():
    """Verify passing empty audio raises InvalidAudioError."""
    provider = GoogleSTTProvider()
    with pytest.raises(InvalidAudioError):
        await provider.transcribe(b"")

    with pytest.raises(InvalidAudioError):
        await provider.transcribe(b"tiny")


# 4. Test Google STT with Mocked speech_recognition
@pytest.mark.asyncio
async def test_google_stt_tamil_success(sample_wav_bytes):
    """Verify Google STT provider handles Tamil transcription."""
    provider = GoogleSTTProvider()

    with patch.object(sr.Recognizer, "record"), \
         patch.object(sr.Recognizer, "recognize_google", return_value="ஜார்விஸ், இன்று என்ன செய்ய வேண்டும்?"):
        result = await provider.transcribe(sample_wav_bytes, language="ta-IN")
        assert result.text == "ஜார்விஸ், இன்று என்ன செய்ய வேண்டும்?"
        assert result.language == "ta-IN"
        assert result.provider == "google"


@pytest.mark.asyncio
async def test_google_stt_unknown_value_silence(sample_wav_bytes):
    """Verify Google STT converts UnknownValueError to NoSpeechDetectedError."""
    provider = GoogleSTTProvider()

    with patch.object(sr.Recognizer, "record"), \
         patch.object(sr.Recognizer, "recognize_google", side_effect=sr.UnknownValueError):
        with pytest.raises(NoSpeechDetectedError):
            await provider.transcribe(sample_wav_bytes, language="ta-IN")


@pytest.mark.asyncio
async def test_google_stt_rate_limit_error(sample_wav_bytes):
    """Verify Google STT handles rate limit quota error."""
    provider = GoogleSTTProvider()

    with patch.object(sr.Recognizer, "record"), \
         patch.object(sr.Recognizer, "recognize_google", side_effect=sr.RequestError("quota exceeded")):
        with pytest.raises(STTRateLimitError):
            await provider.transcribe(sample_wav_bytes, language="ta-IN")


@pytest.mark.asyncio
async def test_google_stt_network_error(sample_wav_bytes):
    """Verify Google STT handles network/connection errors."""
    provider = GoogleSTTProvider()

    with patch.object(sr.Recognizer, "record"), \
         patch.object(sr.Recognizer, "recognize_google", side_effect=sr.RequestError("connection timed out")):
        with pytest.raises(STTProviderError):
            await provider.transcribe(sample_wav_bytes, language="ta-IN")


# 5. Test Groq Whisper STT
@pytest.mark.asyncio
async def test_groq_whisper_missing_api_key(sample_wav_bytes):
    """Verify Groq Whisper raises STTAuthenticationError when API key is missing."""
    provider = GroqWhisperSTTProvider(api_key=None)
    with pytest.raises(STTAuthenticationError):
        await provider.transcribe(sample_wav_bytes)

    empty_key_provider = GroqWhisperSTTProvider(api_key="   ")
    with pytest.raises(STTAuthenticationError):
        await empty_key_provider.transcribe(sample_wav_bytes)


@pytest.mark.asyncio
async def test_groq_whisper_success(sample_wav_bytes):
    """Verify Groq Whisper transcription flow."""
    provider = GroqWhisperSTTProvider(api_key="gsk_test_api_key_123")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "Jarvis, என் project folder open பண்ணு"}

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_response):
        result = await provider.transcribe(sample_wav_bytes, language="ta-IN")
        assert result.text == "Jarvis, என் project folder open பண்ணு"
        assert result.provider == "groq-whisper"


@pytest.mark.asyncio
async def test_groq_whisper_auth_failure(sample_wav_bytes):
    """Verify Groq Whisper handles HTTP 401 Unauthorized."""
    provider = GroqWhisperSTTProvider(api_key="invalid_key")

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(STTAuthenticationError):
            await provider.transcribe(sample_wav_bytes)


@pytest.mark.asyncio
async def test_groq_whisper_rate_limit(sample_wav_bytes):
    """Verify Groq Whisper handles HTTP 429 Rate Limit."""
    provider = GroqWhisperSTTProvider(api_key="valid_key")

    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Rate limited"

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(STTRateLimitError):
            await provider.transcribe(sample_wav_bytes)


@pytest.mark.asyncio
async def test_groq_whisper_timeout(sample_wav_bytes):
    """Verify Groq Whisper handles request timeout."""
    provider = GroqWhisperSTTProvider(api_key="valid_key")

    with patch.object(httpx.AsyncClient, "post", side_effect=httpx.TimeoutException("Timeout")):
        with pytest.raises(STTTimeoutError):
            await provider.transcribe(sample_wav_bytes)


# 6. Test Synchronous Wrapper
def test_transcribe_sync_wrapper(sample_wav_bytes):
    """Verify transcribe_sync wrapper functions correctly."""
    mock_provider = MockSTTProvider(default_response="சரி")
    res = mock_provider.transcribe_sync(sample_wav_bytes)
    assert res.text == "சரி"
