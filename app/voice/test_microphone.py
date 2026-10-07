"""Microphone Diagnostic & Hardware Test (Mode 1).

Checks device availability, queries audio hardware, and tests a live recording burst.
"""

import sys
import time
from typing import Any
import numpy as np

# Configure UTF-8 for Windows terminals
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

from app.voice.microphone import MicrophoneManager, SD_AVAILABLE
from app.voice.audio_config import AudioConfig
from app.voice.exceptions import MicrophoneError, MicrophoneNotFoundError

try:
    import sounddevice as sd
except Exception:
    sd = None


def run_microphone_test() -> bool:
    """Run full microphone diagnostic check."""
    print("=" * 60)
    print("          myoneAI — Microphone Hardware Diagnostic")
    print("=" * 60)

    if not SD_AVAILABLE or sd is None:
        print("[FAIL] sounddevice library is not available or audio driver failed.")
        return False

    print("\n1. Scanning Available Audio Input Devices...")
    mics = MicrophoneManager.list_microphones()
    if not mics:
        print("[FAIL] No microphone input devices found on this system.")
        return False

    for m in mics:
        print(f"   - Device #{m['index']}: {m['name']} (Channels: {m['channels']}, SampleRate: {m['default_samplerate']}Hz)")

    print(f"\n[OK] Found {len(mics)} microphone device(s).")

    print("\n2. Testing 2-Second Live Audio Capture...")
    config = AudioConfig(sample_rate=16000, channels=1, chunk_size=1024)
    mic = MicrophoneManager(config=config)

    energy_readings = []

    def test_callback(indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        if indata.dtype != np.int16:
            scaled = (np.clip(indata, -1.0, 1.0) * 32767).astype(np.int16)
        else:
            scaled = indata
        rms = float(np.sqrt(np.mean(scaled.astype(np.float64) ** 2)))
        energy_readings.append(rms)
        # Visual audio meter
        bars = int(min(20, (rms / 200.0)))
        meter = "#" * bars + "-" * (20 - bars)
        print(f"\r   Audio Level: [{meter}] RMS: {rms:6.1f}", end="", flush=True)

    try:
        with sd.InputStream(
            samplerate=config.sample_rate,
            channels=config.channels,
            dtype=config.dtype,
            blocksize=config.chunk_size,
            callback=test_callback,
        ):
            time.sleep(2.0)
    except Exception as exc:
        print(f"\n[FAIL] Live stream test failed: {exc}")
        return False

    avg_rms = float(np.mean(energy_readings)) if energy_readings else 0.0
    max_rms = float(np.max(energy_readings)) if energy_readings else 0.0
    print(f"\n\n[OK] Capture successful! Avg RMS: {avg_rms:.1f}, Peak RMS: {max_rms:.1f}")

    print("\n" + "=" * 60)
    print("  Result: Microphone subsystem is OPERATIONAL [PASS]")
    print("=" * 60 + "\n")
    return True


if __name__ == "__main__":
    success = run_microphone_test()
    sys.exit(0 if success else 1)
