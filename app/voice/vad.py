"""Lightweight Voice Activity Detector (VAD) for real-time speech detection.

Computes RMS amplitude and adaptive energy thresholds to detect speech start and end
with minimal CPU footprint on 8GB RAM / i3 CPU.
"""

import collections
import logging
import time
from enum import Enum
from typing import Deque, List, Optional
import numpy as np

from app.voice.audio_config import AudioConfig, DEFAULT_AUDIO_CONFIG

logger = logging.getLogger("myoneAI.voice.vad")


class VADState(str, Enum):
    """VAD processing states."""
    WAITING_FOR_SPEECH = "waiting_for_speech"
    SPEECH_DETECTED = "speech_detected"
    SPEECH_ENDED = "speech_ended"
    TIMEOUT = "timeout"


class VoiceActivityDetector:
    """Energy-based VAD with rolling pre-speech padding and adaptive thresholding."""

    def __init__(self, config: Optional[AudioConfig] = None) -> None:
        self.config = config or DEFAULT_AUDIO_CONFIG
        self.state: VADState = VADState.WAITING_FOR_SPEECH

        # Pre-speech buffer to retain audio immediately before trigger
        padding_frames = max(1, int(self.config.pre_speech_padding_sec * self.config.sample_rate / self.config.chunk_size))
        self._pre_speech_buffer: Deque[bytes] = collections.deque(maxlen=padding_frames)
        self._recorded_frames: List[bytes] = []

        self._speech_start_time: Optional[float] = None
        self._last_speech_time: Optional[float] = None
        self._recording_start_time: float = time.time()
        self._ambient_noise_level: float = self.config.start_threshold / 2.0
        self._dynamic_threshold: float = self.config.start_threshold

    @staticmethod
    def calculate_rms(audio_chunk: bytes) -> float:
        """Calculate Root Mean Square (RMS) energy level of 16-bit PCM chunk."""
        if not audio_chunk:
            return 0.0
        try:
            samples = np.frombuffer(audio_chunk, dtype=np.int16)
            if len(samples) == 0:
                return 0.0
            # Use float64 to avoid overflow during squaring
            mean_square = np.mean(samples.astype(np.float64) ** 2)
            return float(np.sqrt(mean_square))
        except Exception:
            return 0.0

    def reset(self) -> None:
        """Reset VAD state for a fresh recording session."""
        self.state = VADState.WAITING_FOR_SPEECH
        self._pre_speech_buffer.clear()
        self._recorded_frames.clear()
        self._speech_start_time = None
        self._last_speech_time = None
        self._recording_start_time = time.time()

    def calibrate_ambient_noise(self, noise_chunks: List[bytes]) -> float:
        """Calibrate dynamic threshold based on ambient background noise chunks."""
        if not noise_chunks:
            return self._dynamic_threshold

        energies = [self.calculate_rms(c) for c in noise_chunks if c]
        if energies:
            avg_noise = float(np.mean(energies))
            self._ambient_noise_level = avg_noise
            # Dynamic threshold is ambient noise + margin or minimum configured threshold
            self._dynamic_threshold = max(self.config.start_threshold, avg_noise * 1.8 + 200.0)
            logger.debug(
                "VAD Calibrated: Ambient=%.1f, Dynamic Threshold=%.1f",
                self._ambient_noise_level,
                self._dynamic_threshold,
            )
        return self._dynamic_threshold

    def process_chunk(self, chunk: bytes) -> VADState:
        """Process an audio chunk and update speech state.

        Args:
            chunk: 16-bit PCM audio bytes.

        Returns:
            Current VADState.
        """
        now = time.time()
        rms = self.calculate_rms(chunk)
        is_speech = rms >= self._dynamic_threshold

        # Check total recording timeout
        if now - self._recording_start_time > self.config.max_recording_duration:
            if self._recorded_frames:
                self.state = VADState.SPEECH_ENDED
            else:
                self.state = VADState.TIMEOUT
            return self.state

        if self.state == VADState.WAITING_FOR_SPEECH:
            self._pre_speech_buffer.append(chunk)
            if is_speech:
                self.state = VADState.SPEECH_DETECTED
                self._speech_start_time = now
                self._last_speech_time = now
                # Transfer pre-speech buffered frames so beginning words aren't cut
                self._recorded_frames.extend(self._pre_speech_buffer)
                self._pre_speech_buffer.clear()
                self._recorded_frames.append(chunk)
                logger.debug("VAD: Speech started (RMS=%.1f, Threshold=%.1f)", rms, self._dynamic_threshold)

        elif self.state == VADState.SPEECH_DETECTED:
            self._recorded_frames.append(chunk)
            if is_speech:
                self._last_speech_time = now
            else:
                # Silence after speech detected
                silence_elapsed = now - (self._last_speech_time or now)
                speech_duration = now - (self._speech_start_time or now)

                if (
                    silence_elapsed >= self.config.end_silence_duration
                    and speech_duration >= self.config.min_recording_duration
                ):
                    self.state = VADState.SPEECH_ENDED
                    logger.debug(
                        "VAD: Speech ended (Duration=%.2fs, Silence=%.2fs)",
                        speech_duration,
                        silence_elapsed,
                    )

        return self.state

    def get_recorded_audio(self) -> bytes:
        """Return full concatenated PCM audio bytes of the speech segment."""
        return b"".join(self._recorded_frames)
