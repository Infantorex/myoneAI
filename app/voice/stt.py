"""Speech-to-Text (STT) provider interface and concrete cloud implementations.

Supports Tamil ('ta-IN'), English, and Tamil-English mixed speech with zero heavy local model weights.
"""

import asyncio
import io
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Union
import speech_recognition as sr
import httpx

from app.core.config import get_settings
from app.voice.exceptions import (
    InvalidAudioError,
    NoSpeechDetectedError,
    STTAuthenticationError,
    STTError,
    STTProviderError,
    STTRateLimitError,
    STTTimeoutError,
)

logger = logging.getLogger("myoneAI.voice.stt")


@dataclass
class STTResult:
    """Standardized speech recognition output."""
    text: str
    confidence: float = 1.0
    language: str = "ta-IN"
    duration_sec: float = 0.0
    provider: str = "unknown"

    def __str__(self) -> str:
        return self.text


class BaseSTT(ABC):
    """Abstract base interface for all STT providers."""

    @abstractmethod
    async def transcribe(
        self,
        audio_data: Union[bytes, io.BytesIO],
        language: str = "ta-IN",
    ) -> STTResult:
        """Transcribe audio bytes into text asynchronously.

        Args:
            audio_data: WAV formatted audio bytes or in-memory buffer.
            language: Target BCP-47 language tag (e.g. 'ta-IN', 'en-US').

        Returns:
            STTResult object containing recognized text and metadata.
        """
        pass

    def transcribe_sync(
        self,
        audio_data: Union[bytes, io.BytesIO],
        language: str = "ta-IN",
    ) -> STTResult:
        """Synchronous wrapper for transcription."""
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, self.transcribe(audio_data, language))
                return future.result()
        except RuntimeError:
            return asyncio.run(self.transcribe(audio_data, language))


class GoogleSTTProvider(BaseSTT):
    """Ultra-lightweight Google Speech Recognition cloud provider.

    Zero local model weights. Fast, accurate transcription for Tamil (ta-IN) and English.
    """

    def __init__(self, api_key: Optional[str] = None, timeout_sec: float = 8.0) -> None:
        self.api_key = api_key
        self.timeout_sec = timeout_sec
        self.recognizer = sr.Recognizer()

    async def transcribe(
        self,
        audio_data: Union[bytes, io.BytesIO],
        language: str = "ta-IN",
    ) -> STTResult:
        start_time = time.time()
        raw_bytes = audio_data.getvalue() if isinstance(audio_data, io.BytesIO) else audio_data

        if not raw_bytes or len(raw_bytes) < 100:
            raise InvalidAudioError("Audio data is empty or too short for transcription.")

        audio_io = io.BytesIO(raw_bytes)

        def _recognize() -> str:
            try:
                with sr.AudioFile(audio_io) as source:
                    audio_record = self.recognizer.record(source)
                return self.recognizer.recognize_google(
                    audio_record,
                    key=self.api_key if self.api_key else None,
                    language=language,
                )
            except sr.UnknownValueError:
                raise NoSpeechDetectedError("No intelligible speech detected.")
            except sr.RequestError as req_err:
                err_msg = str(req_err).lower()
                if "quota" in err_msg or "rate limit" in err_msg:
                    raise STTRateLimitError(f"Google STT rate limit exceeded: {req_err}") from req_err
                if "invalid key" in err_msg or "auth" in err_msg:
                    raise STTAuthenticationError(f"Google STT auth error: {req_err}") from req_err
                raise STTProviderError(f"Google STT network/service error: {req_err}") from req_err
            except Exception as exc:
                raise STTError(f"Audio processing error: {exc}") from exc
            finally:
                audio_io.close()

        try:
            recognized_text = await asyncio.to_thread(_recognize)
        except (NoSpeechDetectedError, STTRateLimitError, STTAuthenticationError, STTProviderError, STTError):
            raise
        except asyncio.TimeoutError as t_err:
            raise STTTimeoutError(f"Google STT transcription timed out after {self.timeout_sec}s") from t_err
        except Exception as exc:
            raise STTError(f"Unexpected error during transcription: {exc}") from exc

        elapsed = time.time() - start_time
        logger.info("Transcription completed in %.2fs [%s]: '%s'", elapsed, language, recognized_text)

        return STTResult(
            text=recognized_text.strip(),
            confidence=0.95,
            language=language,
            duration_sec=round(elapsed, 2),
            provider="google",
        )


class GroqWhisperSTTProvider(BaseSTT):
    """Groq Cloud Whisper API provider for ultra-fast cloud inference."""

    def __init__(self, api_key: Optional[str] = None, model: str = "whisper-large-v3-turbo", timeout_sec: float = 10.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_sec = timeout_sec

    async def transcribe(
        self,
        audio_data: Union[bytes, io.BytesIO],
        language: str = "ta-IN",
    ) -> STTResult:
        if not self.api_key or not self.api_key.strip():
            raise STTAuthenticationError("Groq STT requires a valid API key.")

        raw_bytes = audio_data.getvalue() if isinstance(audio_data, io.BytesIO) else audio_data
        if not raw_bytes or len(raw_bytes) < 100:
            raise InvalidAudioError("Audio data is empty or too short.")

        start_time = time.time()
        # Map ta-IN to ISO 'ta' for Whisper
        lang_code = language.split("-")[0].lower() if "-" in language else language.lower()

        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        files = {"file": ("audio.wav", raw_bytes, "audio/wav")}
        data = {"model": self.model, "language": lang_code, "response_format": "json"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                response = await client.post(url, headers=headers, files=files, data=data)

            if response.status_code == 401:
                raise STTAuthenticationError("Invalid Groq API key.")
            elif response.status_code == 429:
                raise STTRateLimitError("Groq Whisper rate limit exceeded.")
            elif response.status_code != 200:
                raise STTProviderError(f"Groq Whisper API returned error HTTP {response.status_code}: {response.text}")

            result_json = response.json()
            recognized_text = result_json.get("text", "").strip()

            if not recognized_text:
                raise NoSpeechDetectedError("No speech transcribed by Whisper.")

            elapsed = time.time() - start_time
            return STTResult(
                text=recognized_text,
                confidence=0.98,
                language=language,
                duration_sec=round(elapsed, 2),
                provider="groq-whisper",
            )

        except (STTAuthenticationError, STTRateLimitError, STTProviderError, NoSpeechDetectedError):
            raise
        except httpx.TimeoutException as t_err:
            raise STTTimeoutError(f"Groq Whisper request timed out: {t_err}") from t_err
        except Exception as exc:
            raise STTError(f"Groq Whisper request failed: {exc}") from exc


class MockSTTProvider(BaseSTT):
    """Deterministic Mock STT provider for offline development and CI/CD unit testing."""

    def __init__(self, default_response: str = "ஜார்விஸ், இன்று என்ன செய்ய வேண்டும்?") -> None:
        self.default_response = default_response
        self.call_count = 0
        self.should_fail: Optional[Exception] = None

    async def transcribe(
        self,
        audio_data: Union[bytes, io.BytesIO],
        language: str = "ta-IN",
    ) -> STTResult:
        self.call_count += 1
        if self.should_fail:
            raise self.should_fail

        raw_bytes = audio_data.getvalue() if isinstance(audio_data, io.BytesIO) else audio_data
        if not raw_bytes:
            raise InvalidAudioError("Empty audio data provided to MockSTT.")

        return STTResult(
            text=self.default_response,
            confidence=1.0,
            language=language,
            duration_sec=0.01,
            provider="mock",
        )


def get_stt_provider(provider_name: Optional[str] = None) -> BaseSTT:
    """Factory to instantiate the configured STT provider."""
    settings = get_settings()
    name = (provider_name or settings.stt_provider).lower()

    if name in ("google", "google-stt"):
        return GoogleSTTProvider(api_key=settings.stt_api_key)
    elif name in ("groq", "groq-whisper", "whisper"):
        return GroqWhisperSTTProvider(
            api_key=settings.stt_api_key,
            model=settings.stt_model or "whisper-large-v3-turbo",
        )
    elif name == "mock":
        return MockSTTProvider()
    else:
        raise ValueError(f"Unsupported STT provider: '{name}'. Supported providers: 'google', 'groq', 'mock'.")
