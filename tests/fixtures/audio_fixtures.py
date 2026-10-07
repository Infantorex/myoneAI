"""Synthetic audio test generators."""

import io
import wave
import numpy as np

from app.voice.audio_config import AudioConfig, DEFAULT_AUDIO_CONFIG
from app.voice.microphone import pcm_to_wav_bytes


def generate_synthetic_pcm(
    duration_sec: float = 1.0,
    frequency_hz: float = 440.0,
    amplitude: int = 12000,
    sample_rate: int = 16000,
) -> bytes:
    """Generate 16-bit mono PCM sine wave audio bytes."""
    num_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, num_samples, dtype=np.float32)
    waveform = (np.sin(2 * np.pi * frequency_hz * t) * amplitude).astype(np.int16)
    return waveform.tobytes()


def generate_synthetic_wav(
    duration_sec: float = 1.0,
    frequency_hz: float = 440.0,
    config: AudioConfig = DEFAULT_AUDIO_CONFIG,
) -> bytes:
    """Generate standard WAV format byte stream."""
    pcm = generate_synthetic_pcm(
        duration_sec=duration_sec,
        frequency_hz=frequency_hz,
        sample_rate=config.sample_rate,
    )
    return pcm_to_wav_bytes(pcm, config=config)
