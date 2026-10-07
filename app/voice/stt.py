"""Speech-to-Text (STT) provider interface for Tamil and Tamil-English mixed speech.

Abstracts audio transcription providers to enable lightweight cloud STT.
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseSTT(ABC):
    """Abstract base class for Speech-to-Text providers."""

    @abstractmethod
    async def transcribe(self, audio_data: bytes, language: str = "ta-IN") -> Optional[str]:
        """Transcribe raw audio bytes into text.

        Args:
            audio_data: Raw or WAV audio bytes.
            language: Language code (default 'ta-IN').

        Returns:
            Transcribed text or None if silence/error.
        """
        pass
