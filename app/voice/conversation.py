"""Natural Voice Conversation Loop for myoneAI — Tamil JARVIS.

Integrates Microphone, VAD, Tamil STT, Conversation Manager, and Tamil TTS
into a unified conversational pipeline with state machine protection and clean interrupt handling.
"""

import argparse
import asyncio
import logging
import signal
import sys
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional

# Configure UTF-8 for Windows terminals
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

from app.ai.errors import AIError
from app.ai.manager import ConversationManager, conversation_manager
from app.ai.provider import MockAIProvider
from app.core.config import get_settings
from app.core.events import SystemEvent, VoiceEvent, event_bus
from app.core.state import AssistantState, state_manager
from app.voice.audio_config import AudioConfig, DEFAULT_AUDIO_CONFIG
from app.voice.exceptions import (
    NoSpeechDetectedError,
    STTError,
    TTSError,
    VoiceError,
)
from app.voice.microphone import MicrophoneManager
from app.voice.stt import BaseSTT, MockSTTProvider, get_stt_provider
from app.voice.tts import BaseTTS, MockTTSProvider, TTSManager, tts_manager

logger = logging.getLogger("myoneAI.voice.conversation")


class VoiceLoopState(str, Enum):
    """Detailed pipeline states for the voice conversation loop."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING_SPEECH = "processing_speech"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


class VoiceConversationManager:
    """Coordinates full conversational cycles: Mic -> VAD -> STT -> AI -> TTS -> Speaker."""

    def __init__(
        self,
        microphone: Optional[MicrophoneManager] = None,
        stt: Optional[BaseSTT] = None,
        ai: Optional[ConversationManager] = None,
        tts: Optional[TTSManager] = None,
        language: Optional[str] = None,
        listen_timeout: Optional[float] = None,
    ) -> None:
        settings = get_settings()
        self.language = language or settings.voice_language
        self.listen_timeout = listen_timeout or settings.voice_listen_timeout

        config = AudioConfig(default_language=self.language)
        self.microphone = microphone or MicrophoneManager(config=config)
        self.stt = stt or get_stt_provider()
        self.ai = ai or conversation_manager
        self.tts = tts or tts_manager

        self._loop_state: VoiceLoopState = VoiceLoopState.IDLE
        self._stop_requested = asyncio.Event()
        self._is_running = False
        self._lock = asyncio.Lock()

    @property
    def current_state(self) -> VoiceLoopState:
        """Get the active pipeline state."""
        return self._loop_state

    def _set_state(self, state: VoiceLoopState) -> None:
        """Update internal loop state and core system state manager."""
        self._loop_state = state
        # Map to core AssistantState
        mapped = {
            VoiceLoopState.IDLE: AssistantState.IDLE,
            VoiceLoopState.LISTENING: AssistantState.LISTENING,
            VoiceLoopState.PROCESSING_SPEECH: AssistantState.PROCESSING,
            VoiceLoopState.THINKING: AssistantState.PROCESSING,
            VoiceLoopState.SPEAKING: AssistantState.SPEAKING,
            VoiceLoopState.ERROR: AssistantState.ERROR,
        }.get(state, AssistantState.IDLE)
        state_manager.set_state(mapped)

    def stop(self) -> None:
        """Immediately interrupt any active recording, AI thinking, or speech playback."""
        logger.info("Stopping voice conversation pipeline...")
        self._stop_requested.set()
        try:
            if self.microphone.is_recording:
                self.microphone.stop_recording()
        except Exception:
            pass

        try:
            self.tts.stop()
        except Exception:
            pass

        self._set_state(VoiceLoopState.IDLE)

    async def run_once(self) -> Optional[Dict[str, Any]]:
        """Execute one complete voice turn: Listen -> STT -> AI -> Speak -> Return to IDLE.

        Returns:
            Dictionary with transcript, response, and latency metrics, or None if no speech.
        """
        async with self._lock:
            start_time = time.time()
            turn_metrics: Dict[str, Any] = {
                "transcript": "",
                "response": "",
                "stt_duration": 0.0,
                "ai_duration": 0.0,
                "tts_duration": 0.0,
                "total_duration": 0.0,
            }

            try:
                # ------------------------------------------------------------------
                # 1. LISTENING STAGE
                # ------------------------------------------------------------------
                self._set_state(VoiceLoopState.LISTENING)
                event_bus.emit(VoiceEvent.LISTENING_STARTED)
                logger.info("Listening for speech (Timeout: %.1fs)...", self.listen_timeout)

                try:
                    # Run microphone capture in thread pool to avoid blocking asyncio loop
                    audio_bytes = await asyncio.to_thread(
                        self.microphone.record_phrase,
                        max_duration_sec=self.listen_timeout,
                        vad_enabled=True,
                    )
                except NoSpeechDetectedError:
                    logger.info("No speech detected during listening interval.")
                    return None
                finally:
                    event_bus.emit(VoiceEvent.LISTENING_STOPPED)

                if self._stop_requested.is_set():
                    return None

                # ------------------------------------------------------------------
                # 2. SPEECH RECOGNITION (STT) STAGE
                # ------------------------------------------------------------------
                self._set_state(VoiceLoopState.PROCESSING_SPEECH)
                logger.info("Transcribing speech with STT [%s]...", self.language)
                t_stt = time.time()

                try:
                    stt_res = await self.stt.transcribe(audio_bytes, language=self.language)
                    transcript = stt_res.text.strip()
                except NoSpeechDetectedError:
                    logger.info("STT returned no intelligible text.")
                    return None
                except STTError as stt_err:
                    logger.error("STT transcription error: %s", stt_err)
                    print("\n[STT Error]: Speech recognition unavailable. Please try again.")
                    return None

                turn_metrics["stt_duration"] = round(time.time() - t_stt, 2)
                turn_metrics["transcript"] = transcript
                logger.info("User Said: '%s' (STT: %.2fs)", transcript, turn_metrics["stt_duration"])

                if not transcript or self._stop_requested.is_set():
                    return None

                # ------------------------------------------------------------------
                # 3. AI REASONING & CONVERSATION MANAGER STAGE
                # ------------------------------------------------------------------
                self._set_state(VoiceLoopState.THINKING)
                logger.info("Generating AI response...")
                t_ai = time.time()

                try:
                    ai_reply = await self.ai.respond(transcript)
                except AIError as ai_err:
                    logger.error("AI reasoning error: %s", ai_err)
                    error_msg = "மன்னிக்கவும், AI சேவையை தொடர்புகொள்வதில் சிக்கல் உள்ளது." if self.language.startswith("ta") else "I'm having trouble connecting to my AI service. Please try again."
                    print(f"\n[AI Error]: {error_msg}")
                    await self.tts.speak(error_msg, wait=True)
                    return None

                turn_metrics["ai_duration"] = round(time.time() - t_ai, 2)
                turn_metrics["response"] = ai_reply
                logger.info("JARVIS Replied: '%s' (AI: %.2fs)", ai_reply, turn_metrics["ai_duration"])

                if not ai_reply or self._stop_requested.is_set():
                    return None

                # ------------------------------------------------------------------
                # 4. TEXT-TO-SPEECH (TTS) & AUDIO OUTPUT STAGE
                # ------------------------------------------------------------------
                self._set_state(VoiceLoopState.SPEAKING)
                logger.info("Synthesizing and playing speech...")
                t_tts = time.time()

                try:
                    tts_res = await self.tts.speak(ai_reply, wait=True)
                    turn_metrics["tts_duration"] = tts_res.duration_sec
                except TTSError as tts_err:
                    logger.error("TTS output error: %s", tts_err)
                    print(f"\n[TTS Error]: Unable to speak response ({tts_err})")

                turn_metrics["total_duration"] = round(time.time() - start_time, 2)
                return turn_metrics

            except asyncio.CancelledError:
                logger.info("Voice conversation turn cancelled.")
                raise
            except Exception as exc:
                self._set_state(VoiceLoopState.ERROR)
                logger.error("Unexpected error in voice conversation cycle: %s", exc, exc_info=True)
                return None
            finally:
                self._set_state(VoiceLoopState.IDLE)

    async def run_interactive(
        self,
        on_turn: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        """Run continuous multi-turn interactive conversation loop.

        Exits cleanly on user speech command ('exit', 'quit', 'stop') or when stop() is called.
        """
        self._is_running = True
        self._stop_requested.clear()
        logger.info("Starting interactive voice conversation loop...")

        try:
            while not self._stop_requested.is_set():
                print("\nStatus: READY 🟢")
                print("Listening... (Speak naturally in Tamil or English)")

                turn_data = await self.run_once()

                if turn_data and turn_data.get("transcript"):
                    transcript = turn_data["transcript"].strip()
                    response = turn_data["response"].strip()

                    print(f"\nYou   : {transcript}")
                    print(f"JARVIS: {response}")
                    print(f"[Latency: STT {turn_data['stt_duration']}s | AI {turn_data['ai_duration']}s | Total {turn_data['total_duration']}s]")

                    if on_turn:
                        on_turn(turn_data)

                    # Check for exit commands in speech
                    clean_lower = transcript.lower().strip(".,!?")
                    if clean_lower in ("exit", "quit", "stop", "பை", "நன்றி பை", "போய்ட்டு வரேன்"):
                        print("\nExit command detected. Ending voice conversation...")
                        break

                elif turn_data is None:
                    print("\n[No speech detected / Silence].")

                # Short pause between turns
                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            logger.info("Interactive voice loop task cancelled.")
        finally:
            self._is_running = False
            self.stop()
            logger.info("Interactive voice conversation loop stopped.")


# Global singleton instance
voice_conversation_manager = VoiceConversationManager()


async def main_cli() -> None:
    """CLI Entry point for one-shot and interactive voice conversation."""
    parser = argparse.ArgumentParser(
        prog="conversation",
        description="myoneAI — Tamil JARVIS Natural Voice Conversation Pipeline",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in continuous multi-turn interactive mode",
    )
    parser.add_argument(
        "--language",
        "-l",
        type=str,
        default="ta-IN",
        help="Spoken language code (default: ta-IN)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock providers for offline testing without hardware/APIs",
    )

    args = parser.parse_args()

    print("=" * 65)
    print("      myoneAI — Tamil JARVIS Voice Conversation (Phase 5)")
    print("=" * 65)
    print(f"Language : {args.language}")
    print(f"Mode     : {'Interactive (Multi-Turn)' if args.interactive else 'One-Shot (Single Turn)'}")
    print(f"Engine   : {'Mock (Simulated)' if args.mock else 'Cloud STT / AI / TTS'}")
    print("=" * 65)

    if args.mock:
        mgr = VoiceConversationManager(
            stt=MockSTTProvider(default_response="வணக்கம் Jarvis, இன்று என்ன செய்ய வேண்டும்?"),
            ai=ConversationManager(provider=MockAIProvider()),
            tts=TTSManager(provider=MockTTSProvider()),
            language=args.language,
        )
    else:
        mgr = VoiceConversationManager(language=args.language)

    # Setup clean SIGINT / Ctrl+C handler without stack traces
    loop = asyncio.get_running_loop()

    def handle_sigint() -> None:
        print("\n\nStopping myoneAI voice pipeline...")
        print("Releasing audio resources...")
        mgr.stop()
        print("Goodbye! வணக்கம்.")
        sys.exit(0)

    try:
        if sys.platform != "win32":
            loop.add_signal_handler(signal.SIGINT, handle_sigint)
    except Exception:
        pass

    try:
        if args.interactive:
            print("\nStarting interactive conversation. (Say 'exit' or press Ctrl+C to stop)")
            await mgr.run_interactive()
        else:
            print("\nStatus: READY 🟢")
            print("Speak now... (VAD will detect when you finish speaking)")
            turn = await mgr.run_once()
            if turn and turn.get("transcript"):
                print(f"\nYou   : {turn['transcript']}")
                print(f"JARVIS: {turn['response']}")
                print(f"[Latency: STT {turn['stt_duration']}s | AI {turn['ai_duration']}s | Total {turn['total_duration']}s]")
            else:
                print("\n[No speech detected / Silence].")
            print("\nStatus: READY\n")

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n\nStopping myoneAI...")
        print("Releasing audio resources...")
        mgr.stop()
        print("Goodbye! வணக்கம்.\n")


if __name__ == "__main__":
    try:
        asyncio.run(main_cli())
    except KeyboardInterrupt:
        print("\nProcess terminated.")
        sys.exit(0)
