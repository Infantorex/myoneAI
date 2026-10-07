"""Text-to-Speech (TTS) provider interface for natural Tamil voice output.

Abstracts voice synthesis providers (e.g. Edge-TTS, cloud services).
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseTTS(ABC):
    """Abstract base class for Text-to-Speech synthesis providers."""

    @abstractmethod
    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        """Synthesize text into audio bytes.

        Args:
            text: Tamil/English text to speak.
            voice: Voice model/code identifier.

        Returns:
            Audio bytes (e.g. MP3 / WAV).
        """
        pass

    @abstractmethod
    async def speak(self, text: str, voice: Optional[str] = None) -> None:
        """Synthesize and play audio directly through speakers."""
        pass
