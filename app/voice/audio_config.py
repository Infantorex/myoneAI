"""Centralized Audio and Voice Activity Detection (VAD) Configuration.

Defines standard audio parameters and VAD thresholds to avoid code duplication.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AudioConfig:
    """Standard audio capture and processing parameters."""

    sample_rate: int = 16000          # 16 kHz sample rate (optimal for speech recognition)
    channels: int = 1                 # Mono channel
    sample_width: int = 2             # 16-bit PCM (2 bytes per sample)
    chunk_size: int = 1024            # Frame chunk size for streaming and VAD
    dtype: str = "int16"              # NumPy / sounddevice data type

    # Voice Activity Detection (VAD) defaults
    vad_enabled: bool = True
    start_threshold: float = 500.0    # RMS amplitude threshold to trigger speech start
    end_silence_duration: float = 1.5 # Seconds of continuous silence to stop recording
    max_recording_duration: float = 15.0 # Max recording cutoff in seconds
    min_recording_duration: float = 0.5  # Min duration to avoid accidental clicks
    pre_speech_padding_sec: float = 0.3  # Buffer audio before speech detection so first syllable isn't clipped

    # Language defaults
    default_language: str = "ta-IN"   # Primary: Tamil (India)


# Default singleton instance
DEFAULT_AUDIO_CONFIG = AudioConfig()
