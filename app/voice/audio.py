"""In-Memory Audio Player and Speaker Output Subsystem.

Decodes and streams audio (MP3, WAV) directly in memory with zero permanent disk files.
Supports volume scaling, non-blocking playback, and immediate cancellation.
"""

import asyncio
import io
import logging
import threading
import time
from typing import Any, Dict, List, Optional
import numpy as np

try:
    import sounddevice as sd
    SD_AVAILABLE = True
except (ImportError, OSError):
    sd = None
    SD_AVAILABLE = False

try:
    import miniaudio
    MINIAUDIO_AVAILABLE = True
except ImportError:
    miniaudio = None
    MINIAUDIO_AVAILABLE = False

from app.voice.exceptions import AudioPlaybackError

logger = logging.getLogger("myoneAI.voice.audio")


class AudioPlayer:
    """Thread-safe in-memory audio player with volume control and instant stop."""

    def __init__(self, default_volume: float = 1.0) -> None:
        self.default_volume = max(0.0, min(2.0, default_volume))
        self._lock = threading.Lock()
        self._is_playing = False
        self._stop_requested = threading.Event()
        self._current_stream = None

    @property
    def is_playing(self) -> bool:
        """Check if audio playback is actively ongoing."""
        return self._is_playing

    @staticmethod
    def is_speaker_available() -> bool:
        """Check if any audio output / speaker device is available."""
        if not SD_AVAILABLE or sd is None:
            return False
        try:
            devices = sd.query_devices()
            if isinstance(devices, dict):
                devices = [devices]
            return any(d.get("max_output_channels", 0) > 0 for d in devices)
        except Exception:
            return False

    @staticmethod
    def list_speakers() -> List[Dict[str, Any]]:
        """List available output / speaker devices."""
        if not SD_AVAILABLE or sd is None:
            return []
        try:
            devices = sd.query_devices()
            if isinstance(devices, dict):
                devices = [devices]
            outputs = []
            for idx, dev in enumerate(devices):
                if dev.get("max_output_channels", 0) > 0:
                    outputs.append({
                        "index": idx,
                        "name": dev.get("name", "Unknown"),
                        "channels": dev.get("max_output_channels", 2),
                        "default_samplerate": dev.get("default_samplerate", 44100),
                    })
            return outputs
        except Exception as exc:
            logger.error("Failed to query speaker devices: %s", exc)
            return []

    def stop(self) -> None:
        """Immediately stop and interrupt any active audio playback."""
        with self._lock:
            self._stop_requested.set()
            if SD_AVAILABLE and sd is not None:
                try:
                    sd.stop()
                except Exception:
                    pass
            self._is_playing = False
        logger.debug("Audio playback stopped.")

    def decode_audio_bytes(self, audio_data: bytes) -> tuple[np.ndarray, int]:
        """Decode MP3 or WAV audio bytes into NumPy float32 PCM samples and sample rate.

        Args:
            audio_data: Raw audio file bytes (MP3, WAV).

        Returns:
            Tuple of (samples_array: np.ndarray, sample_rate: int).
        """
        if not audio_data:
            raise AudioPlaybackError("Empty audio buffer provided for playback.")

        # 1. Primary decoder: miniaudio
        if MINIAUDIO_AVAILABLE and miniaudio is not None:
            try:
                if audio_data.startswith(b"RIFF"):
                    decoded = miniaudio.wav_read_s16(audio_data)
                elif audio_data.startswith(b"ID3") or audio_data.startswith(b"\xff"):
                    decoded = miniaudio.mp3_read_s16(audio_data)
                else:
                    # Generic auto-detect decode
                    decoded = miniaudio.decode(audio_data, output_format=miniaudio.SampleFormat.SIGNED16)

                # Convert signed 16-bit PCM bytes to numpy array
                samples_i16 = np.frombuffer(decoded.samples, dtype=np.int16)
                if decoded.nchannels > 1:
                    samples_i16 = samples_i16.reshape(-1, decoded.nchannels)
                # Normalize to float32 (-1.0 to 1.0)
                samples_f32 = samples_i16.astype(np.float32) / 32768.0
                return samples_f32, decoded.sample_rate
            except Exception as exc:
                logger.debug("miniaudio decode failed, attempting fallback: %s", exc)

        # 2. Fallback decoder for standard WAV format using stdlib wave
        try:
            import wave
            with wave.open(io.BytesIO(audio_data), "rb") as wf:
                n_channels = wf.getnchannels()
                samp_width = wf.getsampwidth()
                rate = wf.getframerate()
                frames = wf.readframes(wf.getnframes())

                if samp_width == 2:
                    raw_arr = np.frombuffer(frames, dtype=np.int16)
                    if n_channels > 1:
                        raw_arr = raw_arr.reshape(-1, n_channels)
                    return raw_arr.astype(np.float32) / 32768.0, rate
        except Exception:
            pass

        raise AudioPlaybackError("Unable to decode audio format (unsupported or corrupted audio stream).")

    def play(self, audio_data: bytes, volume: Optional[float] = None, wait: bool = True) -> None:
        """Play audio bytes through system speakers synchronously or asynchronously.

        Args:
            audio_data: MP3 or WAV audio bytes.
            volume: Volume multiplier (0.0 to 2.0). If None, uses default_volume.
            wait: If True, blocks until audio finishes playing; if False, plays in background thread.

        Raises:
            AudioPlaybackError: If audio device is unavailable or stream fails.
        """
        if not SD_AVAILABLE or sd is None:
            raise AudioPlaybackError("sounddevice is not available on this system.")

        # Stop any existing playback first to prevent overlapping audio
        self.stop()

        samples, sample_rate = self.decode_audio_bytes(audio_data)

        # Apply volume scaling
        vol = self.default_volume if volume is None else max(0.0, min(2.0, volume))
        if vol != 1.0:
            samples = np.clip(samples * vol, -1.0, 1.0)

        with self._lock:
            self._stop_requested.clear()
            self._is_playing = True

        def _playback_worker() -> None:
            try:
                sd.play(samples, samplerate=sample_rate)
                # Wait for playback completion while periodically checking stop_requested
                duration = len(samples) / sample_rate
                end_time = time.time() + duration

                while time.time() < end_time:
                    if self._stop_requested.is_set():
                        sd.stop()
                        break
                    time.sleep(0.05)
            except Exception as exc:
                logger.error("Audio playback stream error: %s", exc)
                raise AudioPlaybackError(f"Playback failed: {exc}") from exc
            finally:
                with self._lock:
                    self._is_playing = False

        if wait:
            _playback_worker()
        else:
            threading.Thread(target=_playback_worker, daemon=True).start()

    async def play_async(self, audio_data: bytes, volume: Optional[float] = None) -> None:
        """Asynchronously play audio bytes without blocking the asyncio event loop."""
        await asyncio.to_thread(self.play, audio_data, volume, True)


# Global audio player singleton
audio_player = AudioPlayer()
