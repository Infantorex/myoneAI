"""Unit tests for Microphone Manager (app/voice/microphone.py).
"""

import io
import wave
from unittest.mock import MagicMock, patch
import pytest

from app.voice.audio_config import AudioConfig, DEFAULT_AUDIO_CONFIG
from app.voice.exceptions import (
    MicrophoneBusyError,
    MicrophoneNotFoundError,
    MicrophonePermissionError,
    NoSpeechDetectedError,
)
from app.voice.microphone import MicrophoneManager, pcm_to_wav_bytes


def test_pcm_to_wav_bytes():
    """Verify WAV container generation complies with 16kHz mono 16-bit PCM standard."""
    config = AudioConfig(sample_rate=16000, channels=1, sample_width=2)
    pcm = b"\x00\x00" * 1600 # 0.1s

    wav_bytes = pcm_to_wav_bytes(pcm, config)
    assert len(wav_bytes) > len(pcm)
    assert wav_bytes[:4] == b"RIFF"

    # Verify standard wave headers
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000
        assert wf.getnframes() == 1600


def test_list_microphones_mock():
    """Verify microphone device listing handles sounddevice outputs."""
    mock_devices = [
        {"name": "Realtek Microphone", "max_input_channels": 2, "default_samplerate": 44100},
        {"name": "Speakers Output", "max_input_channels": 0, "default_samplerate": 48000},
    ]

    with patch("app.voice.microphone.SD_AVAILABLE", True), \
         patch("app.voice.microphone.sd.query_devices", return_value=mock_devices):
        mics = MicrophoneManager.list_microphones()
        assert len(mics) == 1
        assert mics[0]["name"] == "Realtek Microphone"
        assert MicrophoneManager.is_available() is True


def test_is_available_false_when_no_devices():
    """Verify is_available returns False when no input channels exist."""
    with patch("app.voice.microphone.SD_AVAILABLE", True), \
         patch("app.voice.microphone.sd.query_devices", return_value=[{"max_input_channels": 0}]):
        assert MicrophoneManager.is_available() is False


def test_microphone_not_found_error():
    """Verify record_phrase raises MicrophoneNotFoundError when no mic is found."""
    mic = MicrophoneManager()
    with patch.object(MicrophoneManager, "is_available", return_value=False):
        with pytest.raises(MicrophoneNotFoundError):
            mic.record_phrase()


def test_microphone_busy_error():
    """Verify duplicate concurrent recording sessions raise MicrophoneBusyError."""
    mic = MicrophoneManager()
    mic._is_recording = True
    mic._lock.acquire()

    try:
        with pytest.raises(MicrophoneBusyError):
            mic.record_phrase()
    finally:
        mic._lock.release()
        mic._is_recording = False


def test_microphone_permission_error():
    """Verify permission denied during stream opening raises MicrophonePermissionError."""
    mic = MicrophoneManager()
    with patch.object(MicrophoneManager, "is_available", return_value=True), \
         patch("app.voice.microphone.sd.InputStream", side_effect=PermissionError("Access denied")):
        with pytest.raises(MicrophonePermissionError):
            mic.record_phrase()


def test_no_speech_detected_error():
    """Verify NoSpeechDetectedError is raised when empty audio is captured."""
    mic = MicrophoneManager()
    mock_stream = MagicMock()
    mock_stream.__enter__.return_value = mock_stream

    with patch.object(MicrophoneManager, "is_available", return_value=True), \
         patch("app.voice.microphone.sd.InputStream", return_value=mock_stream), \
         patch("app.voice.microphone.VoiceActivityDetector.get_recorded_audio", return_value=b""):
        with pytest.raises(NoSpeechDetectedError):
            mic.record_phrase()
