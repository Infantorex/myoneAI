"""Microphone audio capture manager for myoneAI / Tamil JARVIS.

Manages on-demand recording using sounddevice with automatic VAD, thread safety,
and graceful error handling. No continuous background recording.
"""

import io
import logging
import threading
import time
import wave
from typing import Any, Dict, List, Optional
import numpy as np

try:
    import sounddevice as sd
    SD_AVAILABLE = True
except (ImportError, OSError):
    sd = None
    SD_AVAILABLE = False

from app.voice.audio_config import AudioConfig, DEFAULT_AUDIO_CONFIG
from app.voice.exceptions import (
    MicrophoneBusyError,
    MicrophoneError,
    MicrophoneNotFoundError,
    MicrophonePermissionError,
    NoSpeechDetectedError,
)
from app.voice.vad import VoiceActivityDetector, VADState

logger = logging.getLogger("myoneAI.voice.microphone")


def pcm_to_wav_bytes(pcm_data: bytes, config: AudioConfig) -> bytes:
    """Wrap raw 16-bit PCM bytes into standard WAV container."""
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wav_file:
        wav_file.setnchannels(config.channels)
        wav_file.setsampwidth(config.sample_width)
        wav_file.setframerate(config.sample_rate)
        wav_file.writeframes(pcm_data)
    return wav_io.getvalue()


class MicrophoneManager:
    """Thread-safe microphone capture manager."""

    def __init__(
        self,
        config: Optional[AudioConfig] = None,
        device_index: Optional[int] = None,
    ) -> None:
        self.config = config or DEFAULT_AUDIO_CONFIG
        self.device_index = device_index
        self._lock = threading.Lock()
        self._is_recording = False
        self._stop_event = threading.Event()

    @property
    def is_recording(self) -> bool:
        """Check if an active recording session is underway."""
        return self._is_recording

    @staticmethod
    def is_available() -> bool:
        """Check whether any working microphone input device is available."""
        if not SD_AVAILABLE or sd is None:
            return False
        try:
            devices = sd.query_devices()
            if isinstance(devices, dict):
                devices = [devices]
            return any(d.get("max_input_channels", 0) > 0 for d in devices)
        except Exception:
            return False

    @staticmethod
    def list_microphones() -> List[Dict[str, Any]]:
        """List all available microphone input devices."""
        if not SD_AVAILABLE or sd is None:
            return []
        try:
            devices = sd.query_devices()
            if isinstance(devices, dict):
                devices = [devices]
            inputs = []
            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0:
                    inputs.append({
                        "index": idx,
                        "name": dev.get("name", "Unknown"),
                        "channels": dev.get("max_input_channels", 1),
                        "default_samplerate": dev.get("default_samplerate", 16000),
                    })
            return inputs
        except Exception as exc:
            logger.error("Failed to query audio devices: %s", exc)
            return []

    def stop_recording(self) -> None:
        """Request immediate halt of an ongoing recording session."""
        self._stop_event.set()

    def record_phrase(
        self,
        max_duration_sec: Optional[float] = None,
        vad_enabled: Optional[bool] = None,
        calibrate_noise: bool = True,
    ) -> bytes:
        """Record an utterance using VAD or fixed duration.

        Args:
            max_duration_sec: Optional override for max duration.
            vad_enabled: Whether to auto-stop on silence.
            calibrate_noise: Whether to calibrate dynamic threshold from initial frames.

        Returns:
            WAV audio bytes containing the recorded speech.

        Raises:
            MicrophoneNotFoundError: No microphone available.
            MicrophoneBusyError: A recording is already active.
            MicrophonePermissionError: Permission denied.
            NoSpeechDetectedError: Only silence was recorded.
            MicrophoneError: Audio driver or hardware failure.
        """
        if not self._lock.acquire(blocking=False):
            raise MicrophoneBusyError("Microphone session is already active.")

        try:
            self._is_recording = True
            self._stop_event.clear()

            if not self.is_available():
                raise MicrophoneNotFoundError("No available microphone input device found.")

            max_dur = max_duration_sec or self.config.max_recording_duration
            use_vad = vad_enabled if vad_enabled is not None else self.config.vad_enabled

            vad = VoiceActivityDetector(self.config) if use_vad else None

            logger.info("Starting audio recording (Max: %.1fs, VAD: %s)...", max_dur, use_vad)

            recorded_pcm_chunks: List[bytes] = []
            calibration_chunks: List[bytes] = []

            def audio_callback(indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
                if status:
                    logger.warning("Sounddevice stream status: %s", status)
                # Convert float/int16 array to 16-bit PCM bytes
                if indata.dtype != np.int16:
                    # Clip and scale float32 (-1.0 to 1.0) to int16
                    scaled = (np.clip(indata, -1.0, 1.0) * 32767).astype(np.int16)
                    chunk_bytes = scaled.tobytes()
                else:
                    chunk_bytes = indata.tobytes()

                if vad:
                    # Collect first 5 chunks (~300ms) for ambient noise baseline
                    if calibrate_noise and len(calibration_chunks) < 5:
                        calibration_chunks.append(chunk_bytes)
                        if len(calibration_chunks) == 5:
                            vad.calibrate_ambient_noise(calibration_chunks)

                    vad_state = vad.process_chunk(chunk_bytes)
                    if vad_state in (VADState.SPEECH_ENDED, VADState.TIMEOUT):
                        self._stop_event.set()
                else:
                    recorded_pcm_chunks.append(chunk_bytes)

            try:
                stream = sd.InputStream(
                    samplerate=self.config.sample_rate,
                    channels=self.config.channels,
                    dtype=self.config.dtype,
                    blocksize=self.config.chunk_size,
                    device=self.device_index,
                    callback=audio_callback,
                )
            except PermissionError as p_err:
                raise MicrophonePermissionError(f"Permission denied accessing microphone: {p_err}") from p_err
            except Exception as e_stream:
                raise MicrophoneError(f"Failed to open audio input stream: {e_stream}") from e_stream

            with stream:
                start_time = time.time()
                while not self._stop_event.is_set():
                    elapsed = time.time() - start_time
                    if elapsed >= max_dur:
                        break
                    time.sleep(0.05)

            if vad:
                pcm_data = vad.get_recorded_audio()
            else:
                pcm_data = b"".join(recorded_pcm_chunks)

            if not pcm_data or len(pcm_data) < self.config.sample_rate * self.config.sample_width * self.config.min_recording_duration:
                raise NoSpeechDetectedError("No speech detected during recording interval.")

            wav_bytes = pcm_to_wav_bytes(pcm_data, self.config)
            logger.info("Recording completed successfully (%d bytes WAV).", len(wav_bytes))
            return wav_bytes

        finally:
            self._is_recording = False
            self._stop_event.set()
            self._lock.release()
