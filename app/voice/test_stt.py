"""Speech-to-Text Test Interface (Mode 2: Live Mic & Mode 3: File-based).

Allows testing Tamil and mixed speech transcription without infinite loops.
"""

import argparse
import asyncio
from pathlib import Path
import sys

# Configure UTF-8 for Windows terminals
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

from app.voice.audio_config import AudioConfig
from app.voice.exceptions import NoSpeechDetectedError, VoiceError
from app.voice.microphone import MicrophoneManager
from app.voice.stt import get_stt_provider, BaseSTT


async def run_stt_test(
    file_path: str = None,
    provider_name: str = None,
    language: str = "ta-IN",
) -> bool:
    """Run controlled STT test."""
    print("=" * 60)
    print("         myoneAI — Tamil Speech-to-Text (STT) Test")
    print("=" * 60)

    try:
        stt = get_stt_provider(provider_name)
    except Exception as exc:
        print(f"[FAIL] Could not initialize STT provider '{provider_name}': {exc}")
        return False

    actual_provider = getattr(stt, "__class__", type(stt)).__name__
    print(f"STT Provider : {actual_provider}")
    print(f"Language     : {language}")

    audio_bytes: bytes

    if file_path:
        # Mode 3: File-based test
        target_file = Path(file_path)
        if not target_file.exists():
            print(f"[FAIL] Audio file not found: {target_file}")
            return False
        print(f"\nMode         : File Test ({target_file.name})")
        print(f"Reading audio file ({target_file.stat().st_size} bytes)...")
        audio_bytes = target_file.read_bytes()
    else:
        # Mode 2: Live microphone test
        print("Mode         : Live Microphone Test")
        mic_available = MicrophoneManager.is_available()
        print(f"Microphone   : {'Ready 🟢' if mic_available else 'Not Found 🔴'}")

        if not mic_available:
            print("[FAIL] No microphone detected. Please connect a microphone or use --file <audio.wav>")
            return False

        config = AudioConfig(default_language=language)
        mic = MicrophoneManager(config=config)

        print("\nListening... (Speak in Tamil or English now. VAD will auto-detect speech end)")
        try:
            audio_bytes = mic.record_phrase(max_duration_sec=10.0, vad_enabled=True)
        except NoSpeechDetectedError:
            print("\n[INFO] No speech detected (silence).")
            print("Ready...\n")
            return True
        except VoiceError as v_err:
            print(f"\n[FAIL] Recording error: {v_err}")
            return False

    print("\nTranscribing audio with cloud STT...")
    try:
        result = await stt.transcribe(audio_bytes, language=language)
        print("\n" + "-" * 60)
        print("Recognized Speech:")
        print(f'"{result.text}"')
        print("-" * 60)
        print(f"Duration   : {result.duration_sec}s")
        print(f"Confidence : {result.confidence:.2f}")
        print(f"Provider   : {result.provider}")
        print("-" * 60)
        print("Ready...\n")
        return True
    except NoSpeechDetectedError:
        print("\n[INFO] Cloud STT returned no intelligible speech.")
        print("Ready...\n")
        return True
    except VoiceError as stt_err:
        print(f"\n[FAIL] STT transcription failed: {stt_err}")
        return False


def main() -> None:
    """CLI entrypoint for STT testing."""
    parser = argparse.ArgumentParser(
        prog="test_stt",
        description="myoneAI — Tamil Speech-to-Text Test Interface",
    )
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        default=None,
        help="Path to WAV audio file for file-based transcription (Mode 3)",
    )
    parser.add_argument(
        "--provider",
        "-p",
        type=str,
        default=None,
        help="STT provider override (google, groq, mock)",
    )
    parser.add_argument(
        "--language",
        "-l",
        type=str,
        default="ta-IN",
        help="Target language code (default: ta-IN)",
    )

    args = parser.parse_args()
    success = asyncio.run(
        run_stt_test(
            file_path=args.file,
            provider_name=args.provider,
            language=args.language,
        )
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
