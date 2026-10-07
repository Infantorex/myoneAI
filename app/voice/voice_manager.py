"""Voice Manager orchestrating Wake Word, Microphone, STT, and TTS.

Implements the voice cycle: Idle -> Wake -> Record -> STT -> (AI) -> TTS -> Idle.
"""

import logging
from typing import Optional
from app.voice.stt import BaseSTT
from app.voice.tts import BaseTTS
from app.voice.wake_word import BaseWakeWord
from app.voice.microphone import MicrophoneManager

logger = logging.getLogger("myoneAI.voice.manager")


class VoiceManager:
    """Coordinates voice input and output components."""

    def __init__(
        self,
        stt: Optional[BaseSTT] = None,
        tts: Optional[BaseTTS] = None,
        wake_word: Optional[BaseWakeWord] = None,
        microphone: Optional[MicrophoneManager] = None,
    ) -> None:
        self.stt = stt
        self.tts = tts
        self.wake_word = wake_word
        self.microphone = microphone or MicrophoneManager()
        self._is_active = False

    @property
    def is_active(self) -> bool:
        """Check if voice listening loop is running."""
        return self._is_active
