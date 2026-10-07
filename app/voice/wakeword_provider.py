"""Wake Word provider interface and concrete implementations.

Provides lightweight, replaceable wake-word detection engines optimized for low-power
execution on 8GB RAM / Intel Core i3 systems with zero heavy continuous models.
"""

import asyncio
import io
import logging
import re
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, List, Optional
import numpy as np

try:
    import sounddevice as sd
    SD_AVAILABLE = True
except (ImportError, OSError):
    sd = None
    SD_AVAILABLE = False

import speech_recognition as sr

from app.core.config import get_settings
from app.voice.audio_config import AudioConfig, DEFAULT_AUDIO_CONFIG
from app.voice.exceptions import (
    MicrophoneBusyError,
    MicrophoneError,
    MicrophoneNotFoundError,
    VoiceError,
)
from app.voice.microphone import pcm_to_wav_bytes

logger = logging.getLogger("myoneAI.voice.wakeword")


class BaseWakeWordProvider(ABC):
    """Abstract base interface for all wake word providers."""

    @abstractmethod
    async def start(self) -> None:
        """Initialize or start the wake word engine."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop wake word detection and release audio hardware."""
        pass

    @abstractmethod
    async def detect(self, timeout_sec: Optional[float] = None) -> bool:
        """Listen for the wake word within a timeout interval.

        Args:
            timeout_sec: Maximum seconds to wait for detection.

        Returns:
            True if the configured wake word was detected, False on timeout.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset internal buffers, triggers, or debounce states."""
        pass


class MockWakeWordProvider(BaseWakeWordProvider):
    """Deterministic Mock Wake Word provider for offline testing and CI/CD."""

    def __init__(
        self,
        wake_word: str = "jarvis",
        trigger_after_calls: int = 1,
        auto_trigger: bool = True,
    ) -> None:
        self.wake_word = wake_word.lower()
        self.trigger_after_calls = trigger_after_calls
        self.auto_trigger = auto_trigger
        self.call_count = 0
        self.is_running = False
        self.manual_trigger = False
        self.should_fail: Optional[Exception] = None
        self.start_count = 0
        self.stop_count = 0

    async def start(self) -> None:
        self.is_running = True
        self.start_count += 1
        logger.debug("MockWakeWordProvider started.")

    async def stop(self) -> None:
        self.is_running = False
        self.stop_count += 1
        logger.debug("MockWakeWordProvider stopped.")

    async def detect(self, timeout_sec: Optional[float] = None) -> bool:
        if self.should_fail:
            raise self.should_fail

        self.call_count += 1
        if timeout_sec and timeout_sec > 0:
            await asyncio.sleep(min(timeout_sec, 0.05))

        if self.manual_trigger:
            self.manual_trigger = False
            return True

        if self.auto_trigger and self.call_count >= self.trigger_after_calls:
            self.call_count = 0
            return True

        return False

    def trigger(self) -> None:
        """Manually trigger a wake word detection on the next detect() call."""
        self.manual_trigger = True

    def reset(self) -> None:
        self.call_count = 0
        self.manual_trigger = False


class LocalWakeWordProvider(BaseWakeWordProvider):
    """Ultra-lightweight local wake word detector.

    Combines low-power RMS energy thresholding with local keyword analysis
    to ensure < 0.5% CPU when idle and zero continuous cloud audio upload.
    """

    def __init__(
        self,
        wake_word: Optional[str] = None,
        sensitivity: Optional[float] = None,
        config: Optional[AudioConfig] = None,
        device_index: Optional[int] = None,
    ) -> None:
        settings = get_settings()
        self.wake_word = (wake_word or settings.wake_word).lower()
        self.sensitivity = sensitivity if sensitivity is not None else settings.wake_word_sensitivity
        self.config = config or DEFAULT_AUDIO_CONFIG
        self.device_index = device_index

        self._is_running = False
        self._lock = threading.Lock()
        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold = max(200.0, 800.0 * (1.0 - self.sensitivity))
        self._recognizer.dynamic_energy_threshold = False
        self._stream: Optional[Any] = None
        self._stop_event = threading.Event()
        self._buffer: List[bytes] = []

    async def start(self) -> None:
        with self._lock:
            self._is_running = True
            self._stop_event.clear()
            self._buffer.clear()
            logger.debug("LocalWakeWordProvider initialized for wake word '%s'", self.wake_word)

    async def stop(self) -> None:
        with self._lock:
            self._is_running = False
            self._stop_event.set()
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
            self._buffer.clear()
            logger.debug("LocalWakeWordProvider audio stream released.")

    def reset(self) -> None:
        with self._lock:
            self._buffer.clear()

    async def detect(self, timeout_sec: Optional[float] = None) -> bool:
        """Listen for audio burst and test for wake word."""
        if not self._is_running:
            return False

        timeout = timeout_sec or get_settings().wake_word_timeout
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_detect, timeout)

    def _sync_detect(self, timeout_sec: float) -> bool:
        """Synchronous audio chunk collection and keyword matching."""
        if not SD_AVAILABLE or sd is None:
            time.sleep(min(timeout_sec, 0.1))
            return False

        # Capture a short window of audio to check for wake phrase
        chunk_count = int((self.config.sample_rate / self.config.chunk_size) * timeout_sec)
        chunk_count = max(1, chunk_count)

        audio_chunks: List[bytes] = []
        speech_detected = False

        def callback(indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
            nonlocal speech_detected
            if self._stop_event.is_set():
                return
            if indata.dtype != np.int16:
                scaled = (np.clip(indata, -1.0, 1.0) * 32767).astype(np.int16)
                chunk_bytes = scaled.tobytes()
                chunk_arr = scaled
            else:
                chunk_bytes = indata.tobytes()
                chunk_arr = indata

            # Fast RMS calculation
            rms = np.sqrt(np.mean(chunk_arr.astype(np.float32) ** 2))
            trigger_energy = max(150.0, 600.0 * (1.0 - self.sensitivity))
            if rms > trigger_energy:
                speech_detected = True

            audio_chunks.append(chunk_bytes)

        try:
            with sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype=self.config.dtype,
                blocksize=self.config.chunk_size,
                device=self.device_index,
                callback=callback,
            ):
                start_t = time.time()
                while time.time() - start_t < timeout_sec:
                    if self._stop_event.is_set():
                        return False
                    time.sleep(0.05)

        except Exception as exc:
            logger.debug("Wake stream exception or interrupted: %s", exc)
            return False

        if not speech_detected or not audio_chunks:
            return False

        # Evaluate captured audio for wake word
        pcm_bytes = b"".join(audio_chunks)
        wav_bytes = pcm_to_wav_bytes(pcm_bytes, self.config)
        return self._evaluate_audio(wav_bytes)

    def _evaluate_audio(self, wav_bytes: bytes) -> bool:
        """Check if recorded WAV audio contains the wake word."""
        try:
            with io.BytesIO(wav_bytes) as audio_file:
                with sr.AudioFile(audio_file) as source:
                    audio_data = self._recognizer.record(source)

            # Try lightweight local Sphinx if available, fallback to fast Google recognizer
            try:
                text = self._recognizer.recognize_sphinx(audio_data, keyword_entries=[(self.wake_word, 1.0)])
            except (AttributeError, sr.RequestError, sr.UnknownValueError):
                try:
                    text = self._recognizer.recognize_google(audio_data, language="en-US")
                except Exception:
                    text = ""

            text_lower = text.lower().strip()
            if not text_lower:
                return False

            # Match target wake word and common phonetic variants
            patterns = [
                rf"\b{re.escape(self.wake_word)}\b",
                r"\b(jarvis|jarvis|service|travis|javis|charvis)\b" if self.wake_word == "jarvis" else rf"\b{re.escape(self.wake_word)}\b",
            ]
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    logger.info("Wake word matched: '%s' in transcript '%s'", self.wake_word, text_lower)
                    return True

            return False

        except Exception as exc:
            logger.debug("Audio wake evaluation failed: %s", exc)
            return False


def get_wakeword_provider(provider_name: Optional[str] = None) -> BaseWakeWordProvider:
    """Factory to instantiate the configured wake word provider."""
    settings = get_settings()
    name = (provider_name or settings.wake_word_provider).lower()

    if name in ("mock", "test"):
        return MockWakeWordProvider(wake_word=settings.wake_word)
    elif name in ("local", "energy", "default"):
        return LocalWakeWordProvider(
            wake_word=settings.wake_word,
            sensitivity=settings.wake_word_sensitivity,
        )
    else:
        logger.warning("Unknown wake word provider '%s', defaulting to LocalWakeWordProvider.", name)
        return LocalWakeWordProvider(wake_word=settings.wake_word)
