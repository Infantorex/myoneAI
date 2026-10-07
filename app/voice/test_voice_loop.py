"""Test utility for the Natural Voice Conversation Loop (Phase 5).

Supports live testing and offline mock pipeline simulation.
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

from app.ai.manager import ConversationManager
from app.ai.provider import MockAIProvider
from app.voice.conversation import VoiceConversationManager
from app.voice.microphone import MicrophoneManager
from app.voice.stt import MockSTTProvider
from app.voice.tts import MockTTSProvider, TTSManager


async def run_voice_loop_test(is_mock: bool = False, language: str = "ta-IN") -> bool:
    """Run simulated or live voice loop test."""
    print("=" * 65)
    print("      myoneAI — Voice Conversation Loop Test (Phase 5)")
    print("=" * 65)
    print(f"Mode     : {'Mock Simulation (Offline)' if is_mock else 'Live Hardware/Cloud'}")
    print(f"Language : {language}")
    print("=" * 65)

    if is_mock:
        print("\n1. Initializing Mock Pipeline...")
        mock_stt = MockSTTProvider(default_response="வணக்கம் Jarvis, இன்று என்ன செய்ய வேண்டும்?")
        mock_ai = ConversationManager(provider=MockAIProvider())
        mock_tts = TTSManager(provider=MockTTSProvider())

        mgr = VoiceConversationManager(
            stt=mock_stt,
            ai=mock_ai,
            tts=mock_tts,
            language=language,
        )

        print("2. Simulating User Utterance: 'வணக்கம் Jarvis, இன்று என்ன செய்ய வேண்டும்?'")
        print("3. Executing State Flow: IDLE -> LISTENING -> STT -> THINKING -> SPEAKING -> IDLE")

        # Mocking audio capture directly for offline simulation
        with (
            patch_mic := getattr(sys, "_mock_mic", None)
            or unittest_mock_mic()
        ):
            turn = await mgr.run_once()

        if turn and turn.get("transcript"):
            print("\n[SUCCESS] Voice loop cycle executed successfully:")
            print(f"  Transcript : \"{turn['transcript']}\"")
            print(f"  AI Reply   : \"{turn['response']}\"")
            print(f"  STT Time   : {turn['stt_duration']}s")
            print(f"  AI Time    : {turn['ai_duration']}s")
            print(f"  TTS Time   : {turn['tts_duration']}s")
            print(f"  Total Time : {turn['total_duration']}s")
            print("\nResult: Voice Loop Pipeline [PASS]\n")
            return True
        else:
            print("\n[FAIL] Voice turn failed to produce output.")
            return False
    else:
        mgr = VoiceConversationManager(language=language)
        print("\nStatus: READY 🟢")
        print("Speak now (e.g. 'வணக்கம் Jarvis')...")
        turn = await mgr.run_once()

        if turn and turn.get("transcript"):
            print(f"\nYou   : {turn['transcript']}")
            print(f"JARVIS: {turn['response']}")
            print(f"\nResult: Live Voice Loop [PASS]\n")
            return True
        else:
            print("\n[INFO] No speech detected or loop interrupted.")
            return True


def unittest_mock_mic():
    """Helper context manager returning synthetic audio for test."""
    from contextlib import contextmanager
    from unittest.mock import patch
    from app.voice.microphone import pcm_to_wav_bytes
    from app.voice.audio_config import DEFAULT_AUDIO_CONFIG

    sample_pcm = b"\x00\x00" * 8000
    sample_wav = pcm_to_wav_bytes(sample_pcm, DEFAULT_AUDIO_CONFIG)

    @contextmanager
    def _cm():
        with patch.object(MicrophoneManager, "is_available", return_value=True), \
             patch.object(MicrophoneManager, "record_phrase", return_value=sample_wav):
            yield

    return _cm()


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="test_voice_loop",
        description="myoneAI — Natural Voice Conversation Loop Test Utility",
    )
    parser.add_argument(
        "--mock",
        "-m",
        action="store_true",
        help="Run offline mock pipeline test without microphone or API keys",
    )
    parser.add_argument(
        "--language",
        "-l",
        type=str,
        default="ta-IN",
        help="Spoken language code (default: ta-IN)",
    )

    args = parser.parse_args()
    success = asyncio.run(run_voice_loop_test(is_mock=args.mock, language=args.language))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
