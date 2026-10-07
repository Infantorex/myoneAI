"""Tamil Text-to-Speech (TTS) Test Interface.

Allows interactive and command-line testing of natural Tamil, English, and mixed speech synthesis.
"""

import argparse
import asyncio
import sys

# Configure UTF-8 for Windows terminals
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

from app.core.config import get_settings
from app.voice.exceptions import TTSError, VoiceError
from app.voice.tts import TTSManager, get_tts_provider


async def run_tts_test(
    text: str = None,
    provider_name: str = None,
    voice: str = None,
    language: str = "ta-IN",
    speed: float = 1.0,
    volume: float = 1.0,
) -> bool:
    """Execute TTS synthesis and speaker playback."""
    settings = get_settings()
    selected_provider_name = provider_name or settings.tts_provider
    selected_voice = voice or (
        "en-US-JennyNeural" if language.startswith("en") else settings.tts_voice
    )

    print("=" * 60)
    print("        myoneAI — Tamil Text-to-Speech (TTS) Test")
    print("=" * 60)
    print(f"Provider : {selected_provider_name}")
    print(f"Language : {language}")
    print(f"Voice    : {selected_voice}")
    print(f"Speed    : {speed}x | Volume: {volume}x")
    print("=" * 60)

    try:
        provider = get_tts_provider(selected_provider_name)
        manager = TTSManager(provider=provider)
    except Exception as exc:
        print(f"[FAIL] Failed to initialize TTS subsystem: {exc}")
        return False

    # If no text provided, enter interactive mode
    if not text:
        default_prompt = "வணக்கம் Infanto, எப்படி இருக்கிறீர்கள்?"
        print(f"\nEnter text to speak (Press Enter for default: '{default_prompt}'):")
        try:
            user_input = input("> ").strip()
            text_to_speak = user_input if user_input else default_prompt
        except (EOFError, KeyboardInterrupt):
            print("\nTest cancelled.")
            return True
    else:
        text_to_speak = text

    print(f"\nText: \"{text_to_speak}\"")
    print("Generating speech...")

    try:
        print("Playing through speakers...")
        result = await manager.speak(
            text=text_to_speak,
            voice=selected_voice,
            rate=speed,
            volume=volume,
            wait=True,
        )
        print("-" * 60)
        print(f"Synthesis Duration : {result.duration_sec}s")
        print(f"Audio Format       : {result.format.upper()} ({len(result.audio_bytes)} bytes)")
        print(f"Voice Used         : {result.voice}")
        print("-" * 60)
        print("TTS test completed successfully [PASS].\n")
        return True
    except TTSError as tts_err:
        print(f"\n[FAIL] TTS Error: {tts_err}")
        return False
    except VoiceError as v_err:
        print(f"\n[FAIL] Voice Subsystem Error: {v_err}")
        return False
    except Exception as exc:
        print(f"\n[FAIL] Unexpected Error: {exc}")
        return False


def main() -> None:
    """CLI parser and entry point."""
    parser = argparse.ArgumentParser(
        prog="test_tts",
        description="myoneAI — Tamil Text-to-Speech Test Utility",
    )
    parser.add_argument(
        "--text",
        "-t",
        type=str,
        default=None,
        help="Text string to synthesize and speak",
    )
    parser.add_argument(
        "--provider",
        "-p",
        type=str,
        default=None,
        help="TTS provider override (edge-tts, mock)",
    )
    parser.add_argument(
        "--voice",
        "-v",
        type=str,
        default=None,
        help="Voice code override (e.g. ta-IN-PallaviNeural, ta-IN-ValluvarNeural)",
    )
    parser.add_argument(
        "--language",
        "-l",
        type=str,
        default="ta-IN",
        help="Language code (default: ta-IN)",
    )
    parser.add_argument(
        "--speed",
        "-s",
        type=float,
        default=1.0,
        help="Speech speed multiplier (default: 1.0)",
    )
    parser.add_argument(
        "--volume",
        type=float,
        default=1.0,
        help="Speech volume multiplier (default: 1.0)",
    )

    args = parser.parse_args()
    success = asyncio.run(
        run_tts_test(
            text=args.text,
            provider_name=args.provider,
            voice=args.voice,
            language=args.language,
            speed=args.speed,
            volume=args.volume,
        )
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
