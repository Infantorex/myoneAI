"""Structured exceptions for Voice, Microphone, and STT subsystems.

Ensures that errors in audio capture or cloud transcription never crash the assistant.
"""


class VoiceError(Exception):
    """Base exception for all voice subsystem errors."""
    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        return f"{self.message} ({self.details})" if self.details else self.message


class MicrophoneError(VoiceError):
    """Generic microphone error."""
    pass


class MicrophoneNotFoundError(MicrophoneError):
    """No working microphone detected on the system."""
    pass


class MicrophonePermissionError(MicrophoneError):
    """Permission denied when accessing the microphone."""
    pass


class MicrophoneBusyError(MicrophoneError):
    """Microphone is already in use by another session."""
    pass


class NoSpeechDetectedError(VoiceError):
    """Audio recorded was pure silence with no speech detected."""
    pass


class AudioTimeoutError(VoiceError):
    """Audio recording exceeded maximum time limit without completion."""
    pass


class InvalidAudioError(VoiceError):
    """Audio data format is corrupted or unsupported."""
    pass


class STTError(VoiceError):
    """Generic Speech-to-Text error."""
    pass


class STTTimeoutError(STTError):
    """Cloud STT service timed out during transcription."""
    pass


class STTProviderError(STTError):
    """STT provider returned an error or failed to process audio."""
    pass


class STTAuthenticationError(STTError):
    """Invalid or missing API key for the STT provider."""
    pass


class STTRateLimitError(STTError):
    """API rate limit exceeded for STT provider."""
    pass
