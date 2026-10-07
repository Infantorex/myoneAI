"""JARVIS Voice Assistant Interactive Runtime (Phase 6).

Integrates low-power Wake Word listening with natural Voice Conversation loop.
"""

import argparse
import asyncio
import logging
import signal
import sys
import time

# Configure UTF-8 for Windows terminals
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

from app.ai.manager import ConversationManager, conversation_manager
from app.ai.provider import MockAIProvider
from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.voice.conversation import VoiceConversationManager, voice_conversation_manager
from app.voice.microphone import MicrophoneManager
from app.voice.stt import MockSTTProvider
from app.voice.tts import MockTTSProvider, TTSManager, tts_manager
from app.voice.wakeword_manager import WakeWordManager
from app.voice.wakeword_provider import (
    LocalWakeWordProvider,
    MockWakeWordProvider,
)

logger = logging.getLogger("myoneAI.voice.jarvis")


async def run_jarvis(
    is_mock: bool = False,
    wake_word: str = "jarvis",
    language: str = "ta-IN",
    max_turns: int = 0,
) -> None:
    """Run full JARVIS wake word + conversation assistant runtime."""
    settings = get_settings()
    target_phrase = (wake_word or settings.wake_word).upper()

    print("=" * 40)
    print("myoneAI JARVIS")
    print("=" * 40)
    print(f"Wake word: {target_phrase}")
    print(f"Language : {language}")
    print(f"Engine   : {'Mock (Offline Simulation)' if is_mock else 'Cloud / Local Real Hardware'}")
    print("Status   : READY\n")

    if is_mock:
        mock_stt = MockSTTProvider(default_response="வணக்கம் Jarvis, இன்று என்ன செய்யலாம்?")
        mock_ai = ConversationManager(
            provider=MockAIProvider(default_response="வணக்கம் Infanto! நல்லா இருக்கேன். நீங்கள் எப்படி இருக்கீங்க?")
        )
        mock_tts = TTSManager(provider=MockTTSProvider())
        conv_mgr = VoiceConversationManager(
            stt=mock_stt,
            ai=mock_ai,
            tts=mock_tts,
            language=language,
        )
        wake_prov = MockWakeWordProvider(wake_word=target_phrase.lower(), trigger_after_calls=1)
        manager = WakeWordManager(
            provider=wake_prov,
            conversation_manager=conv_mgr,
            tts=mock_tts,
            wake_word=target_phrase.lower(),
        )
    else:
        conv_mgr = VoiceConversationManager(language=language)
        wake_prov = LocalWakeWordProvider(wake_word=target_phrase.lower())
        manager = WakeWordManager(
            provider=wake_prov,
            conversation_manager=conv_mgr,
            tts=tts_manager,
            wake_word=target_phrase.lower(),
        )

    stop_event = asyncio.Event()

    def handle_interrupt(*_: object) -> None:
        print("\n\nStopping JARVIS...")
        print("Releasing audio resources...")
        stop_event.set()
        asyncio.create_task(manager.stop())

    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            asyncio.get_running_loop().add_signal_handler(sig, handle_interrupt)

    await manager.start()

    turn_count = 0
    try:
        print("Waiting for wake word...")
        while not stop_event.is_set():
            detected = await manager.wait_for_wake_word(timeout_sec=0.5)
            if detected:
                turn_count += 1
                print("\nWake word detected.")

                if is_mock:
                    # Provide synthetic mic capture for mock run
                    from unittest.mock import patch
                    from app.voice.audio_config import DEFAULT_AUDIO_CONFIG
                    from app.voice.microphone import pcm_to_wav_bytes
                    sample_wav = pcm_to_wav_bytes(b"\x00\x00" * 8000, DEFAULT_AUDIO_CONFIG)

                    with patch.object(MicrophoneManager, "is_available", return_value=True), \
                         patch.object(MicrophoneManager, "record_phrase", return_value=sample_wav):
                        turn = await manager.trigger_conversation()
                else:
                    turn = await manager.trigger_conversation()

                if turn and turn.get("transcript"):
                    print(f"You   : {turn['transcript']}")
                    print(f"JARVIS: {turn['response']}\n")
                else:
                    print("[No speech processed]\n")

                if max_turns > 0 and turn_count >= max_turns:
                    break

                print("Waiting for wake word...")

            await asyncio.sleep(0.05)

    except (KeyboardInterrupt, asyncio.CancelledError):
        handle_interrupt()
    finally:
        await manager.stop()
        print("JARVIS stopped.")


def main() -> None:
    """CLI entrypoint."""
    setup_logging()
    parser = argparse.ArgumentParser(
        prog="jarvis",
        description="myoneAI — Tamil JARVIS Voice Assistant",
    )
    parser.add_argument(
        "--mock",
        "-m",
        action="store_true",
        help="Run offline mock simulation mode without microphone",
    )
    parser.add_argument(
        "--wake-word",
        "-w",
        type=str,
        default="jarvis",
        help="Wake phrase (default: jarvis)",
    )
    parser.add_argument(
        "--language",
        "-l",
        type=str,
        default="ta-IN",
        help="Spoken language (default: ta-IN)",
    )

    args = parser.parse_args()
    try:
        asyncio.run(run_jarvis(is_mock=args.mock, wake_word=args.wake_word, language=args.language))
    except KeyboardInterrupt:
        print("\nJARVIS stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
