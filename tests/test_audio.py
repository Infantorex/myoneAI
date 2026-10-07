"""Unit tests for in-memory audio player (app/voice/audio.py).
"""

from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from app.voice.audio import AudioPlayer
from app.voice.audio_config import DEFAULT_AUDIO_CONFIG
from app.voice.exceptions import AudioPlaybackError
from app.voice.microphone import pcm_to_wav_bytes


@pytest.fixture
def valid_wav_bytes() -> bytes:
    """Generate 0.2s 16kHz mono WAV bytes."""
    t = np.linspace(0, 0.2, 3200, False)
    pcm = (np.sin(2 * np.pi * 440 * t) * 4000).astype(np.int16).tobytes()
    return pcm_to_wav_bytes(pcm, DEFAULT_AUDIO_CONFIG)


def test_decode_valid_wav(valid_wav_bytes):
    """Verify AudioPlayer successfully decodes standard WAV bytes."""
    player = AudioPlayer()
    samples, sample_rate = player.decode_audio_bytes(valid_wav_bytes)

    assert sample_rate == 16000
    assert isinstance(samples, np.ndarray)
    assert len(samples) == 3200
    assert samples.dtype == np.float32


def test_decode_empty_bytes_raises_error():
    """Verify decoding empty bytes raises AudioPlaybackError."""
    player = AudioPlayer()
    with pytest.raises(AudioPlaybackError):
        player.decode_audio_bytes(b"")


def test_list_speakers_and_availability():
    """Verify speaker listing and query handling."""
    mock_devices = [
        {"name": "Realtek Speakers", "max_output_channels": 2, "default_samplerate": 48000},
        {"name": "Microphone", "max_output_channels": 0, "default_samplerate": 16000},
    ]

    with patch("app.voice.audio.SD_AVAILABLE", True), \
         patch("app.voice.audio.sd.query_devices", return_value=mock_devices):
        speakers = AudioPlayer.list_speakers()
        assert len(speakers) == 1
        assert speakers[0]["name"] == "Realtek Speakers"
        assert AudioPlayer.is_speaker_available() is True


def test_player_play_and_stop_lifecycle(valid_wav_bytes):
    """Verify play and stop lifecycle with mocked sounddevice."""
    player = AudioPlayer(default_volume=1.0)

    with patch("app.voice.audio.SD_AVAILABLE", True), \
         patch("app.voice.audio.sd.play") as mock_sd_play, \
         patch("app.voice.audio.sd.stop") as mock_sd_stop:

        # Synchronous play
        player.play(valid_wav_bytes, volume=0.8, wait=True)
        assert mock_sd_play.called

        # Stop
        player.stop()
        assert mock_sd_stop.called
        assert player.is_playing is False


@pytest.mark.asyncio
async def test_player_play_async(valid_wav_bytes):
    """Verify play_async executes without errors."""
    player = AudioPlayer()

    with patch("app.voice.audio.SD_AVAILABLE", True), \
         patch("app.voice.audio.sd.play"):
        await player.play_async(valid_wav_bytes)
        assert player.is_playing is False
