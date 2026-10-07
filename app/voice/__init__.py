"""Voice module for myoneAI / Tamil JARVIS.

Provides provider-independent interfaces for Tamil/English STT, TTS, audio playback,
microphone capture, VAD, wake-word detection, and natural voice conversation loop.
"""

from typing import TYPE_CHECKING, Any

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

if TYPE_CHECKING:
    from app.voice.conversation import (
        VoiceConversationManager,
        VoiceLoopState,
        voice_conversation_manager,
    )
    from app.voice.wakeword_manager import (
        WakeWordManager,
        WakeWordState,
        wake_word_manager,
    )
    from app.voice.wakeword_provider import (
        BaseWakeWordProvider,
        LocalWakeWordProvider,
        MockWakeWordProvider,
        get_wakeword_provider,
    )


def __getattr__(name: str) -> Any:
    """Lazy load conversation and wakeword symbols to prevent circular import warnings."""
    if name in ("VoiceConversationManager", "VoiceLoopState", "voice_conversation_manager"):
        import app.voice.conversation as conv
        return getattr(conv, name)
    elif name in ("WakeWordManager", "WakeWordState", "wake_word_manager"):
        import app.voice.wakeword_manager as wwm
        return getattr(wwm, name)
    elif name in ("BaseWakeWordProvider", "LocalWakeWordProvider", "MockWakeWordProvider", "get_wakeword_provider"):
        import app.voice.wakeword_provider as wwp
        return getattr(wwp, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "AudioConfig",
    "DEFAULT_AUDIO_CONFIG",
    "AudioPlayer",
    "audio_player",
    "VoiceConversationManager",
    "VoiceLoopState",
    "voice_conversation_manager",
    "WakeWordManager",
    "WakeWordState",
    "wake_word_manager",
    "BaseWakeWordProvider",
    "LocalWakeWordProvider",
    "MockWakeWordProvider",
    "get_wakeword_provider",
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
