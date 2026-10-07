"""Wake Word Test CLI Utility (Phase 6).

Supports live hardware detection and offline mock simulation.
"""

import argparse
import asyncio
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

from app.core.config import get_settings
from app.voice.wakeword_manager import WakeWordManager
from app.voice.wakeword_provider import (
    LocalWakeWordProvider,
    MockWakeWordProvider,
)


async def run_wakeword_test(is_mock: bool = False, wake_word: str = "jarvis") -> None:
    """Run wake word detection test loop."""
    settings = get_settings()
    target_phrase = (wake_word or settings.wake_word).upper()

    print("=" * 40)
    print("myoneAI Wake Word Test")
    print("=" * 40)
    print(f"Wake word: {target_phrase}")
    print(f"Engine   : {'Mock Provider (Offline)' if is_mock else 'Local Energy/Speech'}")
    print(f"Status   : LISTENING\n")

    if is_mock:
        provider = MockWakeWordProvider(wake_word=target_phrase.lower(), trigger_after_calls=2)
    else:
        provider = LocalWakeWordProvider(wake_word=target_phrase.lower())

    manager = WakeWordManager(provider=provider, wake_word=target_phrase.lower())

    stop_event = asyncio.Event()

    def handle_interrupt(*_: object) -> None:
        print("\n\nStopping wake word test...")
        print("Releasing audio resources...")
        stop_event.set()
        asyncio.create_task(manager.stop())

    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            asyncio.get_running_loop().add_signal_handler(sig, handle_interrupt)

    await manager.start()

    if not is_mock:
        print(f"Say \"{target_phrase.title()}\"...\n")
    else:
        print("Simulating wake triggers offline...\n")

    detections = 0
    try:
        while not stop_event.is_set():
            detected = await manager.wait_for_wake_word(timeout_sec=0.5)
            if detected:
                detections += 1
                print(f"Wake word detected! (Count: {detections})")
                print("Status: ACTIVATED")
                await asyncio.sleep(0.8)
                print("\nStatus: LISTENING")
                if not is_mock:
                    print(f"Say \"{target_phrase.title()}\"...\n")
                if is_mock and detections >= 2:
                    break

            await asyncio.sleep(0.05)

    except (KeyboardInterrupt, asyncio.CancelledError):
        handle_interrupt()
    finally:
        await manager.stop()
        print("Goodbye.")


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="test_wakeword",
        description="myoneAI — Lightweight Wake Word Test Utility",
    )
    parser.add_argument(
        "--mock",
        "-m",
        action="store_true",
        help="Run offline mock wake word test without microphone",
    )
    parser.add_argument(
        "--wake-word",
        "-w",
        type=str,
        default="jarvis",
        help="Target wake phrase to test (default: jarvis)",
    )

    args = parser.parse_args()
    try:
        asyncio.run(run_wakeword_test(is_mock=args.mock, wake_word=args.wake_word))
    except KeyboardInterrupt:
        print("\nGoodbye.")
        sys.exit(0)


if __name__ == "__main__":
    main()
