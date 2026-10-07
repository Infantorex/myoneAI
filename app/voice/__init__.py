"""Voice module for myoneAI / Tamil JARVIS.

Provides provider-independent interfaces for Tamil/English STT, TTS, microphone, and wake-word.
"""

from app.voice.stt import BaseSTT
from app.voice.tts import BaseTTS
from app.voice.wake_word import BaseWakeWord
from app.voice.microphone import MicrophoneManager
from app.voice.voice_manager import VoiceManager

__all__ = [
    "BaseSTT",
    "BaseTTS",
    "BaseWakeWord",
    "MicrophoneManager",
    "VoiceManager",
]
