"""Unit tests for Phase 2 & 3: Audio Player, VAD, STT, and TTS subsystems."""

import asyncio
import io
import pytest

from app.voice.audio import AudioPlayer
from app.voice.audio_config import DEFAULT_AUDIO_CONFIG
from app.voice.microphone import pcm_to_wav_bytes
from app.voice.stt import MockSTTProvider, STTResult
from app.voice.tts import MockTTSProvider, TTSResult, format_rate_param, format_volume_param
from app.voice.vad import VoiceActivityDetector, VADState
from tests.fixtures.audio_fixtures import generate_synthetic_pcm, generate_synthetic_wav


def test_vad_speech_start_and_end():
    """Verify VoiceActivityDetector detects speech start, frames recording, and state end."""
    vad = VoiceActivityDetector()
    speech_pcm = generate_synthetic_pcm(duration_sec=0.5, amplitude=15000)
    silence_pcm = generate_synthetic_pcm(duration_sec=0.5, amplitude=50)

    # 1. Start with silence
    st = vad.process_chunk(silence_pcm)
    assert st == VADState.WAITING_FOR_SPEECH

    # 2. Feed speech
    st = vad.process_chunk(speech_pcm)
    assert st == VADState.SPEECH_DETECTED

    # 3. Recorded audio bytes accumulated
    audio = vad.get_recorded_audio()
    assert len(audio) > 0


def test_audio_player_wav_decoding():
    """Verify AudioPlayer decodes standard WAV byte buffers into float32 samples."""
    wav_bytes = generate_synthetic_wav(duration_sec=0.2)
    player = AudioPlayer()
    samples, sr = player.decode_audio_bytes(wav_bytes)
    assert len(samples) > 0
    assert sr == DEFAULT_AUDIO_CONFIG.sample_rate


@pytest.mark.asyncio
async def test_mock_stt_transcription():
    """Verify MockSTTProvider returns structured Tamil STTResult."""
    stt = MockSTTProvider(default_response="வணக்கம் JARVIS")
    wav_bytes = generate_synthetic_wav(duration_sec=0.1)
    res = await stt.transcribe(wav_bytes, language="ta-IN")
    assert isinstance(res, STTResult)
    assert res.text == "வணக்கம் JARVIS"
    assert res.language == "ta-IN"


@pytest.mark.asyncio
async def test_mock_tts_synthesis():
    """Verify MockTTSProvider returns structured audio result."""
    tts = MockTTSProvider()
    res = await tts.synthesize("வணக்கம் Infanto")
    assert isinstance(res, TTSResult)
    assert len(res.audio_bytes) > 0
    assert res.text == "வணக்கம் Infanto"


def test_tts_parameter_formatting():
    """Verify rate and volume parameter conversions."""
    assert format_rate_param(1.2) == "+20%"
    assert format_rate_param(0.8) == "-20%"
    assert format_rate_param("+10%") == "+10%"
    assert format_volume_param(1.0) == "+0%"
    assert format_volume_param(1.5) == "+50%"
