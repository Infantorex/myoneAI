"""Wake Word Manager for myoneAI — Tamil JARVIS.

Coordinates low-power wake-word detection, duplicate activation prevention,
microphone ownership handover, and seamless triggering of the voice conversation loop.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional

from app.core.config import get_settings
from app.core.events import SystemEvent, VoiceEvent, event_bus
from app.core.state import AssistantState, ServiceStatus, state_manager
from app.voice.conversation import VoiceConversationManager, voice_conversation_manager
from app.voice.tts import TTSManager, tts_manager
from app.voice.wakeword_provider import (
    BaseWakeWordProvider,
    MockWakeWordProvider,
    get_wakeword_provider,
)

logger = logging.getLogger("myoneAI.voice.wakeword_manager")


class WakeWordState(str, Enum):
    """Lifecycle states for the wake-word listener."""
    IDLE = "idle"
    WAKE_LISTENING = "wake_listening"
    WAKE_DETECTED = "wake_detected"
    ACTIVATING = "activating"
    CONVERSING = "conversing"
    PAUSED = "paused"
    ERROR = "error"


class WakeWordManager:
    """Manages continuous, low-resource wake-word listening and voice loop invocation."""

    def __init__(
        self,
        provider: Optional[BaseWakeWordProvider] = None,
        conversation_manager: Optional[VoiceConversationManager] = None,
        tts: Optional[TTSManager] = None,
        wake_word: Optional[str] = None,
        cooldown_sec: Optional[float] = None,
        wake_response_enabled: Optional[bool] = None,
        wake_response_text: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        self.wake_word = wake_word or settings.wake_word
        self.provider = provider or get_wakeword_provider()
        self.conversation_manager = conversation_manager or voice_conversation_manager
        self.tts = tts or tts_manager

        self.cooldown_sec = cooldown_sec if cooldown_sec is not None else settings.wake_word_cooldown
        self.wake_response_enabled = (
            wake_response_enabled if wake_response_enabled is not None else settings.wake_response_enabled
        )
        self.wake_response_text = wake_response_text or settings.wake_response_text
        self.on_battery_allowed = settings.wake_word_on_battery

        self._state: WakeWordState = WakeWordState.IDLE
        self._is_running = False
        self._stop_event = asyncio.Event()
        self._last_detection_time: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def current_state(self) -> WakeWordState:
        """Get the current wake-word system state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if wake word manager is actively running."""
        return self._is_running

    def _set_state(self, new_state: WakeWordState) -> None:
        """Update internal and global state."""
        old_state = self._state
        self._state = new_state
        logger.debug("WakeWord state transition: %s -> %s", old_state.value, new_state.value)

        # Map to core AssistantState for global telemetry
        if new_state == WakeWordState.WAKE_LISTENING:
            state_manager.set_state(AssistantState.IDLE)
        elif new_state in (WakeWordState.WAKE_DETECTED, WakeWordState.ACTIVATING):
            state_manager.set_state(AssistantState.LISTENING)
        elif new_state == WakeWordState.PAUSED:
            state_manager.set_state(AssistantState.PAUSED)
        elif new_state == WakeWordState.ERROR:
            state_manager.set_state(AssistantState.ERROR)

    def _is_cooldown_active(self) -> bool:
        """Check if minimum cooldown between detections is currently active."""
        elapsed = time.time() - self._last_detection_time
        return elapsed < self.cooldown_sec

    def _check_battery_allowed(self) -> bool:
        """Check if wake listening is permitted based on battery status."""
        if self.on_battery_allowed:
            return True
        metrics = state_manager.get_system_metrics()
        plugged = metrics.get("battery_plugged")
        if plugged is False:
            logger.info("Wake word listening paused because laptop is running on battery power.")
            return False
        return True

    async def start(self) -> None:
        """Initialize and start the wake word engine."""
        async with self._lock:
            if self._is_running:
                return
            self._is_running = True
            self._stop_event.clear()
            await self.provider.start()
            self._set_state(WakeWordState.WAKE_LISTENING)
            state_manager.set_service_status("wake_word", ServiceStatus.RUNNING)
            logger.info("Wake word service started for phrase '%s'.", self.wake_word)

    async def stop(self) -> None:
        """Safely stop wake-word listening and release resources."""
        async with self._lock:
            self._is_running = False
            self._stop_event.set()
            try:
                await self.provider.stop()
            except Exception as exc:
                logger.error("Error stopping wake word provider: %s", exc)
            self._set_state(WakeWordState.IDLE)
            state_manager.set_service_status("wake_word", ServiceStatus.STOPPED)
            logger.info("Wake word service stopped.")

    async def wait_for_wake_word(self, timeout_sec: Optional[float] = None) -> bool:
        """Wait for a single wake word occurrence.

        Args:
            timeout_sec: Optional maximum duration to wait.

        Returns:
            True if detected without cooldown conflict, False otherwise.
        """
        if not self._check_battery_allowed():
            if timeout_sec:
                await asyncio.sleep(timeout_sec)
            return False

        if not self._is_running:
            await self.start()

        self._set_state(WakeWordState.WAKE_LISTENING)
        try:
            detected = await self.provider.detect(timeout_sec=timeout_sec)
            if detected:
                if self._is_cooldown_active():
                    logger.debug("Duplicate wake word ignored due to active cooldown (%.2fs)", self.cooldown_sec)
                    return False

                self._last_detection_time = time.time()
                self._set_state(WakeWordState.WAKE_DETECTED)
                event_bus.emit(VoiceEvent.WAKE_WORD_DETECTED, {"wake_word": self.wake_word})
                logger.info("Wake word '%s' detected successfully.", self.wake_word)
                return True
            return False

        except Exception as exc:
            logger.error("Error during wake word detection: %s", exc, exc_info=True)
            self._set_state(WakeWordState.ERROR)
            await asyncio.sleep(0.5)
            self._set_state(WakeWordState.WAKE_LISTENING)
            return False

    async def trigger_conversation(self) -> Optional[Dict[str, Any]]:
        """Acknowledge wake detection and execute one voice conversation cycle.

        Ensures strict microphone ownership handover:
        1. Pause/Release wake-word detector audio.
        2. Speak short wake response if enabled.
        3. Hand over microphone to VoiceConversationManager.
        4. Resume wake detector audio once conversation finishes.
        """
        self._set_state(WakeWordState.ACTIVATING)

        try:
            # 1. Release wake-word microphone stream
            await self.provider.stop()

            # 2. Optional acknowledgement response
            if self.wake_response_enabled and self.wake_response_text:
                try:
                    logger.debug("Speaking wake response acknowledgement: %s", self.wake_response_text)
                    await self.tts.speak(self.wake_response_text)
                except Exception as tts_err:
                    logger.warning("Wake acknowledgement speech failed: %s", tts_err)

            # 3. Handover to Conversation Manager
            self._set_state(WakeWordState.CONVERSING)
            turn_result = await self.conversation_manager.run_once()
            return turn_result

        except Exception as exc:
            logger.error("Error during voice conversation cycle after wake trigger: %s", exc, exc_info=True)
            self._set_state(WakeWordState.ERROR)
            return None

        finally:
            # 4. Resume wake detector audio stream
            if self._is_running:
                try:
                    await self.provider.start()
                    self._set_state(WakeWordState.WAKE_LISTENING)
                except Exception as start_err:
                    logger.error("Failed to restart wake detector after conversation: %s", start_err)
                    self._set_state(WakeWordState.ERROR)
            else:
                self._set_state(WakeWordState.IDLE)

    async def listen_loop(
        self,
        on_wake_detected: Optional[Callable[[], Any]] = None,
        max_iterations: Optional[int] = None,
    ) -> None:
        """Run continuous wake word detection loop.

        Args:
            on_wake_detected: Optional callback invoked immediately upon wake detection.
            max_iterations: Optional iteration limit (primarily for testing).
        """
        await self.start()
        iterations = 0

        logger.info("Entering continuous wake listening loop for '%s'...", self.wake_word)
        try:
            while self._is_running and not self._stop_event.is_set():
                if max_iterations is not None and iterations >= max_iterations:
                    break

                detected = await self.wait_for_wake_word(timeout_sec=get_settings().wake_word_timeout)
                if detected:
                    iterations += 1
                    if on_wake_detected:
                        try:
                            if asyncio.iscoroutinefunction(on_wake_detected):
                                await on_wake_detected()
                            else:
                                on_wake_detected()
                        except Exception as cb_err:
                            logger.error("Error in on_wake_detected callback: %s", cb_err)

                    # Trigger full conversation cycle with clean mic handover
                    await self.trigger_conversation()

                await asyncio.sleep(0.02)

        except asyncio.CancelledError:
            logger.info("Wake word listening loop cancelled.")
        finally:
            await self.stop()


# Global wake word manager singleton
wake_word_manager = WakeWordManager()
