"""Microphone audio capture manager for myoneAI.

Manages recording audio on-demand with automatic silence detection without continuous background streaming.
"""

import logging
from typing import Optional

logger = logging.getLogger("myoneAI.voice.microphone")


class MicrophoneManager:
    """Manages audio capture lifecycle."""

    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024) -> None:
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self._is_recording = False

    @property
    def is_recording(self) -> bool:
        """Check if recording is active."""
        return self._is_recording

    def record_phrase(self, max_duration_sec: float = 10.0) -> Optional[bytes]:
        """Record audio until silence is detected or max duration is reached."""
        logger.debug("MicrophoneManager record_phrase requested (max %ss)", max_duration_sec)
        return None
