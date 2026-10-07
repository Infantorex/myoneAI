"""Text-to-Speech (TTS) subsystem for natural Tamil, English, and mixed speech.

Provides provider-independent synthesis interfaces, Edge-TTS cloud neural engine,
mock provider for testing, and central TTSManager with overlap protection.
"""

import asyncio
import io
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Union
import numpy as np

from app.core.config import get_settings
from app.core.events import VoiceEvent, event_bus
from app.voice.audio import AudioPlayer, audio_player
from app.voice.audio_config import DEFAULT_AUDIO_CONFIG
from app.voice.exceptions import (
    EmptyTextError,
    TextTooLongError,
    TTSAuthenticationError,
    TTSConfigurationError,
    TTSError,
    TTSProviderError,
    TTSTimeoutError,
)
from app.voice.microphone import pcm_to_wav_bytes

logger = logging.getLogger("myoneAI.voice.tts")


@dataclass
class TTSResult:
    """Standardized Text-to-Speech synthesis output."""
    audio_bytes: bytes
    text: str
    voice: str = "ta-IN-PallaviNeural"
    format: str = "mp3"
    duration_sec: float = 0.0
    provider: str = "unknown"


def format_rate_param(rate_val: Union[float, str, None]) -> str:
    """Convert float or string rate to edge-tts rate parameter (e.g. 1.2 -> '+20%')."""
    if rate_val is None:
        return "+0%"
    if isinstance(rate_val, str):
        return rate_val if rate_val.endswith("%") else f"{rate_val}%"
    try:
        pct = int(round((float(rate_val) - 1.0) * 100))
        return f"+{pct}%" if pct >= 0 else f"{pct}%"
    except ValueError:
        return "+0%"


def format_volume_param(vol_val: Union[float, str, None]) -> str:
    """Convert float or string volume to edge-tts volume parameter (e.g. 1.0 -> '+0%')."""
    if vol_val is None:
        return "+0%"
    if isinstance(vol_val, str):
        return vol_val if vol_val.endswith("%") else f"{vol_val}%"
    try:
        pct = int(round((float(vol_val) - 1.0) * 100))
        return f"+{pct}%" if pct >= 0 else f"{pct}%"
    except ValueError:
        return "+0%"


class BaseTTS(ABC):
    """Abstract base class for Text-to-Speech providers."""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: Optional[Union[float, str]] = None,
        volume: Optional[Union[float, str]] = None,
    ) -> TTSResult:
        """Synthesize text into audio bytes asynchronously.

        Args:
            text: Tamil, English, or mixed text to synthesize.
            voice: Voice identifier (e.g. 'ta-IN-PallaviNeural').
            rate: Speech rate modifier (default: 1.0 or '+0%').
            volume: Volume modifier (default: 1.0 or '+0%').

        Returns:
            TTSResult containing audio bytes and metadata.
        """
        pass

    def synthesize_sync(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: Optional[Union[float, str]] = None,
        volume: Optional[Union[float, str]] = None,
    ) -> TTSResult:
        """Synchronous wrapper for speech synthesis."""
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, self.synthesize(text, voice, rate, volume))
                return future.result()
        except RuntimeError:
            return asyncio.run(self.synthesize(text, voice, rate, volume))


class EdgeTTSProvider(BaseTTS):
    """Microsoft Edge Neural TTS cloud provider.

    Zero local model weights. Crystal clear natural Tamil neural voices
    (ta-IN-PallaviNeural, ta-IN-ValluvarNeural) with mixed Tamil-English support.
    """

    DEFAULT_VOICE = "ta-IN-PallaviNeural"

    def __init__(self, default_voice: Optional[str] = None, timeout_sec: float = 30.0) -> None:
        self.default_voice = default_voice or self.DEFAULT_VOICE
        self.timeout_sec = timeout_sec

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: Optional[Union[float, str]] = None,
        volume: Optional[Union[float, str]] = None,
    ) -> TTSResult:
        if not text or not text.strip():
            raise EmptyTextError("Text for speech synthesis cannot be empty.")

        target_voice = voice or self.default_voice
        rate_str = format_rate_param(rate)
        vol_str = format_volume_param(volume)

        start_time = time.time()
        logger.debug("Synthesizing with EdgeTTS [Voice: %s, Rate: %s]: '%s'", target_voice, rate_str, text[:50])

        try:
            import edge_tts
            communicate = edge_tts.Communicate(
                text=text,
                voice=target_voice,
                rate=rate_str,
                volume=vol_str,
            )

            audio_stream = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_stream.write(chunk["data"])

            audio_bytes = audio_stream.getvalue()
            if not audio_bytes:
                raise TTSProviderError("EdgeTTS returned empty audio stream.")

            elapsed = time.time() - start_time
            logger.info("EdgeTTS synthesized %d bytes in %.2fs [%s]", len(audio_bytes), elapsed, target_voice)

            return TTSResult(
                audio_bytes=audio_bytes,
                text=text,
                voice=target_voice,
                format="mp3",
                duration_sec=round(elapsed, 2),
                provider="edge-tts",
            )

        except asyncio.TimeoutError as t_err:
            raise TTSTimeoutError(f"EdgeTTS request timed out after {self.timeout_sec}s") from t_err
        except (EmptyTextError, TTSTimeoutError, TTSProviderError):
            raise
        except Exception as exc:
            logger.error("EdgeTTS synthesis error: %s", exc)
            raise TTSProviderError(f"EdgeTTS synthesis failed: {exc}") from exc


class MockTTSProvider(BaseTTS):
    """Deterministic Mock TTS provider for offline testing and CI/CD without network."""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate
        self.call_count = 0
        self.last_synthesized_text: Optional[str] = None
        self.should_fail: Optional[Exception] = None

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: Optional[Union[float, str]] = None,
        volume: Optional[Union[float, str]] = None,
    ) -> TTSResult:
        self.call_count += 1
        self.last_synthesized_text = text

        if self.should_fail:
            raise self.should_fail

        if not text or not text.strip():
            raise EmptyTextError("Text for speech synthesis cannot be empty.")

        # Generate 0.2s synthetic sine wave WAV bytes
        t = np.linspace(0, 0.2, int(self.sample_rate * 0.2), False)
        pcm = (np.sin(2 * np.pi * 440 * t) * 3000).astype(np.int16).tobytes()
        wav_bytes = pcm_to_wav_bytes(pcm, DEFAULT_AUDIO_CONFIG)

        return TTSResult(
            audio_bytes=wav_bytes,
            text=text,
            voice=voice or "mock-voice",
            format="wav",
            duration_sec=0.2,
            provider="mock",
        )


def get_tts_provider(provider_name: Optional[str] = None) -> BaseTTS:
    """Factory to instantiate the configured TTS provider."""
    settings = get_settings()
    name = (provider_name or settings.tts_provider).lower()

    if name in ("edge", "edge-tts", "edgetts"):
        return EdgeTTSProvider(
            default_voice=settings.tts_voice,
            timeout_sec=settings.tts_timeout,
        )
    elif name == "mock":
        return MockTTSProvider()
    else:
        raise TTSConfigurationError(f"Unsupported TTS provider: '{name}'. Supported: 'edge-tts', 'mock'.")


class TTSManager:
    """Coordinates text validation, speech synthesis, and audio playback.

    Guarantees no overlapping speech output and safe resource cleanup.
    """

    def __init__(
        self,
        provider: Optional[BaseTTS] = None,
        player: Optional[AudioPlayer] = None,
        max_text_length: int = 1000,
    ) -> None:
        self.provider = provider or get_tts_provider()
        self.player = player or audio_player
        self.max_text_length = max_text_length
        self._lock = asyncio.Lock()

    def sanitize_text(self, text: str, max_length: Optional[int] = None) -> str:
        """Validate, trim, and normalize text before speech synthesis.

        Preserves Tamil Unicode, English characters, digits, and standard punctuation.
        """
        if not text:
            raise EmptyTextError("Speech text cannot be empty.")

        # Normalize excessive whitespace
        cleaned = re.sub(r"\s+", " ", text).strip()
        if not cleaned:
            raise EmptyTextError("Speech text contains only whitespace.")

        limit = max_length if max_length is not None else getattr(self, "max_text_length", 1000)
        if len(cleaned) > limit:
            raise TextTooLongError(f"Text length ({len(cleaned)}) exceeds maximum allowed ({limit} chars).")

        return cleaned

    def is_speaking(self) -> bool:
        """Check if speech audio is currently playing."""
        return self.player.is_playing

    def stop(self) -> None:
        """Immediately stop any active speech playback."""
        self.player.stop()

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: Optional[Union[float, str]] = None,
        volume: Optional[Union[float, str]] = None,
    ) -> TTSResult:
        """Sanitize text and synthesize audio without playing."""
        clean_text = self.sanitize_text(text, self.max_text_length)
        return await self.provider.synthesize(clean_text, voice=voice, rate=rate, volume=volume)

    async def speak(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: Optional[Union[float, str]] = None,
        volume: Optional[Union[float, str]] = None,
        wait: bool = True,
    ) -> TTSResult:
        """Synthesize text and play audio through speakers.

        Ensures no overlapping speech by halting previous playback.

        Args:
            text: Text to speak.
            voice: Voice identifier override.
            rate: Speech rate modifier.
            volume: Volume level modifier.
            wait: If True, awaits audio playback completion.

        Returns:
            TTSResult object.
        """
        async with self._lock:
            # 1. Stop any currently active speech before starting new one
            if self.is_speaking():
                self.stop()

            # 2. Synthesize audio
            result = await self.synthesize(text, voice=voice, rate=rate, volume=volume)

            # 3. Emit event & Play
            event_bus.emit(VoiceEvent.TTS_STARTED, {"text": text, "voice": result.voice})

            try:
                if wait:
                    await self.player.play_async(result.audio_bytes)
                else:
                    self.player.play(result.audio_bytes, wait=False)
            finally:
                event_bus.emit(VoiceEvent.TTS_FINISHED, {"text": text})

            return result

    def speak_sync(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: Optional[Union[float, str]] = None,
        volume: Optional[Union[float, str]] = None,
    ) -> TTSResult:
        """Synchronous speak helper."""
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, self.speak(text, voice, rate, volume, True))
                return future.result()
        except RuntimeError:
            return asyncio.run(self.speak(text, voice, rate, volume, True))


# Global TTS manager singleton
tts_manager = TTSManager()
