"""Unit tests for Voice Activity Detection (app/voice/vad.py).
"""

import time
import numpy as np
import pytest

from app.voice.audio_config import AudioConfig
from app.voice.vad import VoiceActivityDetector, VADState


def make_pcm_chunk(amplitude: int = 0, samples: int = 1024) -> bytes:
    """Generate a PCM chunk of specified amplitude."""
    arr = np.full(samples, amplitude, dtype=np.int16)
    return arr.tobytes()


def make_sine_chunk(freq: float = 440.0, sample_rate: int = 16000, samples: int = 1024, amp: float = 5000.0) -> bytes:
    """Generate a sine wave chunk with clear audible energy."""
    t = np.linspace(0, samples / sample_rate, samples, False)
    arr = (np.sin(2 * np.pi * freq * t) * amp).astype(np.int16)
    return arr.tobytes()


def test_rms_calculation():
    """Verify RMS calculation accuracy."""
    silence = make_pcm_chunk(0)
    assert VoiceActivityDetector.calculate_rms(silence) == 0.0

    loud = make_pcm_chunk(2000)
    assert pytest.approx(VoiceActivityDetector.calculate_rms(loud), 1.0) == 2000.0

    sine = make_sine_chunk(amp=10000.0)
    rms_sine = VoiceActivityDetector.calculate_rms(sine)
    assert rms_sine > 6000.0


def test_vad_noise_calibration():
    """Verify adaptive threshold calibration."""
    cfg = AudioConfig(start_threshold=400.0)
    vad = VoiceActivityDetector(cfg)

    # Ambient noise chunks with ~100 RMS
    noise_chunks = [make_pcm_chunk(100) for _ in range(5)]
    dyn_thresh = vad.calibrate_ambient_noise(noise_chunks)

    # Threshold should adapt upward to be above ambient noise
    assert dyn_thresh > 100.0


def test_vad_speech_detection_and_end_lifecycle():
    """Verify full state cycle: waiting -> speech detected -> speech ended."""
    cfg = AudioConfig(
        start_threshold=500.0,
        end_silence_duration=0.2, # Short silence for fast unit test
        min_recording_duration=0.1,
        max_recording_duration=5.0,
    )
    vad = VoiceActivityDetector(cfg)

    # 1. Initial silence -> WAITING_FOR_SPEECH
    silence_chunk = make_pcm_chunk(0)
    assert vad.process_chunk(silence_chunk) == VADState.WAITING_FOR_SPEECH

    # 2. Loud speech chunk -> SPEECH_DETECTED
    speech_chunk = make_sine_chunk(amp=3000.0)
    assert vad.process_chunk(speech_chunk) == VADState.SPEECH_DETECTED

    # 3. Ongoing speech
    assert vad.process_chunk(speech_chunk) == VADState.SPEECH_DETECTED

    # 4. Silence after speech
    # Simulate time passing beyond end_silence_duration and min_recording_duration
    vad._speech_start_time = time.time() - 1.0
    vad._last_speech_time = time.time() - 0.5
    assert vad.process_chunk(silence_chunk) == VADState.SPEECH_ENDED

    # Verify recorded audio buffer contains frames
    audio_data = vad.get_recorded_audio()
    assert len(audio_data) > 0


def test_vad_timeout():
    """Verify timeout when maximum recording duration is exceeded without speech."""
    cfg = AudioConfig(max_recording_duration=0.1)
    vad = VoiceActivityDetector(cfg)

    silence_chunk = make_pcm_chunk(0)
    # Simulate past start time
    vad._recording_start_time = time.time() - 0.5

    assert vad.process_chunk(silence_chunk) == VADState.TIMEOUT
