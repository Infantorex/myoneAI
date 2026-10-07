"""Voice module for myoneAI / Tamil JARVIS.

Provides provider-independent interfaces for Tamil/English STT, TTS, audio playback,
microphone capture, VAD, and wake-word detection.
"""

from app.voice.audio import AudioPlayer, audio_player
from app.voice.audio_config import AudioConfig, DEFAULT_AUDIO_CONFIG
from app.voice.exceptions import (
    AudioPlaybackError,
    AudioTimeoutError,
    EmptyTextError,
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
    TextTooLongError,
    TTSAuthenticationError,
    TTSConfigurationError,
    TTSError,
    TTSProviderError,
    TTSRateLimitError,
    TTSTimeoutError,
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
from app.voice.tts import (
    BaseTTS,
    EdgeTTSProvider,
    MockTTSProvider,
    TTSManager,
    TTSResult,
    get_tts_provider,
    tts_manager,
)
from app.voice.vad import VADState, VoiceActivityDetector
from app.voice.voice_manager import VoiceManager
from app.voice.wake_word import BaseWakeWord

__all__ = [
    "AudioConfig",
    "DEFAULT_AUDIO_CONFIG",
    "AudioPlayer",
    "audio_player",
    "VoiceError",
    "MicrophoneError",
    "MicrophoneNotFoundError",
    "MicrophonePermissionError",
    "MicrophoneBusyError",
    "NoSpeechDetectedError",
    "AudioTimeoutError",
    "InvalidAudioError",
    "AudioPlaybackError",
    "STTError",
    "STTTimeoutError",
    "STTProviderError",
    "STTAuthenticationError",
    "STTRateLimitError",
    "TTSError",
    "TTSProviderError",
    "TTSConfigurationError",
    "TTSTimeoutError",
    "TTSAuthenticationError",
    "TTSRateLimitError",
    "EmptyTextError",
    "TextTooLongError",
    "BaseSTT",
    "STTResult",
    "GoogleSTTProvider",
    "GroqWhisperSTTProvider",
    "MockSTTProvider",
    "get_stt_provider",
    "BaseTTS",
    "TTSResult",
    "EdgeTTSProvider",
    "MockTTSProvider",
    "TTSManager",
    "tts_manager",
    "get_tts_provider",
    "BaseWakeWord",
    "MicrophoneManager",
    "pcm_to_wav_bytes",
    "VoiceActivityDetector",
    "VADState",
    "VoiceManager",
]
