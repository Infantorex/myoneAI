"""Voice module for myoneAI / Tamil JARVIS.

Provides provider-independent interfaces for Tamil/English STT, TTS, microphone, VAD, and wake-word.
"""

from app.voice.audio_config import AudioConfig, DEFAULT_AUDIO_CONFIG
from app.voice.exceptions import (
    AudioTimeoutError,
    InvalidAudioError,
    MicrophoneBusyError,
    MicrophoneError,
    MicrophoneNotFoundError,
    MicrophonePermissionError,
    NoSpeechDetectedError,
    STTAuthenticationError,
    STTError,
    STTProviderError,
    STTRateLimitError,
    STTTimeoutError,
    VoiceError,
)
from app.voice.microphone import MicrophoneManager, pcm_to_wav_bytes
from app.voice.stt import (
    BaseSTT,
    GoogleSTTProvider,
    GroqWhisperSTTProvider,
    MockSTTProvider,
    STTResult,
    get_stt_provider,
)
from app.voice.tts import BaseTTS
from app.voice.vad import VADState, VoiceActivityDetector
from app.voice.voice_manager import VoiceManager
from app.voice.wake_word import BaseWakeWord

__all__ = [
    "AudioConfig",
    "DEFAULT_AUDIO_CONFIG",
    "VoiceError",
    "MicrophoneError",
    "MicrophoneNotFoundError",
    "MicrophonePermissionError",
    "MicrophoneBusyError",
    "NoSpeechDetectedError",
    "AudioTimeoutError",
    "InvalidAudioError",
    "STTError",
    "STTTimeoutError",
    "STTProviderError",
    "STTAuthenticationError",
    "STTRateLimitError",
    "BaseSTT",
    "STTResult",
    "GoogleSTTProvider",
    "GroqWhisperSTTProvider",
    "MockSTTProvider",
    "get_stt_provider",
    "BaseTTS",
    "BaseWakeWord",
    "MicrophoneManager",
    "pcm_to_wav_bytes",
    "VoiceActivityDetector",
    "VADState",
    "VoiceManager",
]
