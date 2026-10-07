"""Automated unit and integration tests for Wake Word Subsystem (Phase 6).

All external audio hardware, cloud APIs, and background processes are mocked.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.config import Settings
from app.core.events import VoiceEvent, event_bus
from app.core.state import AssistantState, ServiceStatus, state_manager
from app.voice.conversation import VoiceConversationManager
from app.voice.tts import TTSManager
from app.voice.wakeword_manager import WakeWordManager, WakeWordState
from app.voice.wakeword_provider import (
    BaseWakeWordProvider,
    LocalWakeWordProvider,
    MockWakeWordProvider,
    get_wakeword_provider,
)


@pytest.mark.asyncio
async def test_mock_wakeword_provider_lifecycle():
    """Verify MockWakeWordProvider starts, detects, and stops properly."""
    provider = MockWakeWordProvider(wake_word="jarvis", trigger_after_calls=2)
    assert not provider.is_running
    assert provider.start_count == 0

    await provider.start()
    assert provider.is_running
    assert provider.start_count == 1

    # First call - not yet triggered
    detected1 = await provider.detect(timeout_sec=0.01)
    assert not detected1

    # Second call - triggered
    detected2 = await provider.detect(timeout_sec=0.01)
    assert detected2

    # Manual trigger
    provider.trigger()
    detected3 = await provider.detect(timeout_sec=0.01)
    assert detected3

    await provider.stop()
    assert not provider.is_running
    assert provider.stop_count == 1


@pytest.mark.asyncio
async def test_get_wakeword_provider_factory():
    """Verify factory returns appropriate provider based on config or argument."""
    mock_prov = get_wakeword_provider("mock")
    assert isinstance(mock_prov, MockWakeWordProvider)

    test_prov = get_wakeword_provider("test")
    assert isinstance(test_prov, MockWakeWordProvider)

    local_prov = get_wakeword_provider("local")
    assert isinstance(local_prov, LocalWakeWordProvider)


@pytest.mark.asyncio
async def test_wakeword_configuration():
    """Verify wake word manager respects custom wake phrase and cooldown settings."""
    custom_prov = MockWakeWordProvider(wake_word="computer")
    manager = WakeWordManager(
        provider=custom_prov,
        wake_word="computer",
        cooldown_sec=2.0,
        wake_response_enabled=False,
    )
    assert manager.wake_word == "computer"
    assert manager.cooldown_sec == 2.0
    assert not manager.wake_response_enabled


@pytest.mark.asyncio
async def test_wakeword_duplicate_detection_and_cooldown():
    """Verify rapid consecutive wake detections within cooldown window are ignored."""
    prov = MockWakeWordProvider(wake_word="jarvis", trigger_after_calls=1)
    manager = WakeWordManager(provider=prov, cooldown_sec=1.0)

    # First detection -> Success
    detected1 = await manager.wait_for_wake_word(timeout_sec=0.01)
    assert detected1
    assert manager.current_state == WakeWordState.WAKE_DETECTED

    # Immediate second detection -> Ignored due to cooldown
    prov.trigger()
    detected2 = await manager.wait_for_wake_word(timeout_sec=0.01)
    assert not detected2

    # Wait until cooldown expires
    await asyncio.sleep(1.05)
    prov.trigger()
    detected3 = await manager.wait_for_wake_word(timeout_sec=0.01)
    assert detected3


@pytest.mark.asyncio
async def test_state_transitions_and_events():
    """Verify full state machine progression and event emission."""
    prov = MockWakeWordProvider(wake_word="jarvis", trigger_after_calls=1)
    events_received = []

    def on_wake(evt):
        events_received.append(evt.data.get("wake_word"))

    event_bus.subscribe(VoiceEvent.WAKE_WORD_DETECTED, on_wake)

    manager = WakeWordManager(provider=prov, cooldown_sec=0.1)
    assert manager.current_state == WakeWordState.IDLE

    await manager.start()
    assert manager.current_state == WakeWordState.WAKE_LISTENING

    detected = await manager.wait_for_wake_word(timeout_sec=0.01)
    assert detected
    assert manager.current_state == WakeWordState.WAKE_DETECTED
    assert "jarvis" in events_received

    await manager.stop()
    assert manager.current_state == WakeWordState.IDLE
    event_bus.unsubscribe(VoiceEvent.WAKE_WORD_DETECTED, on_wake)


@pytest.mark.asyncio
async def test_microphone_ownership_and_conversation_trigger():
    """Verify that wake provider releases mic before conversation starts, and resumes afterwards."""
    wake_prov = MockWakeWordProvider(wake_word="jarvis")
    mock_conv = MagicMock(spec=VoiceConversationManager)
    mock_conv.run_once = AsyncMock(return_value={
        "transcript": "வணக்கம்",
        "response": "வணக்கம் Infanto!",
        "total_duration": 1.2,
    })

    mock_tts = MagicMock(spec=TTSManager)
    mock_tts.speak = AsyncMock(return_value=None)

    manager = WakeWordManager(
        provider=wake_prov,
        conversation_manager=mock_conv,
        tts=mock_tts,
        wake_response_enabled=True,
        wake_response_text="சொல்லுங்க.",
    )

    await manager.start()
    assert wake_prov.is_running

    # Trigger conversation
    result = await manager.trigger_conversation()

    assert result is not None
    assert result["transcript"] == "வணக்கம்"
    assert result["response"] == "வணக்கம் Infanto!"

    # Verification of handover sequence:
    # 1. Wake acknowledgement TTS spoke
    mock_tts.speak.assert_awaited_once_with("சொல்லுங்க.")

    # 2. Conversation manager was invoked exactly once
    mock_conv.run_once.assert_awaited_once()

    # 3. Wake provider was stopped during conversation and restarted afterwards
    assert wake_prov.stop_count >= 1
    assert wake_prov.start_count >= 2
    assert wake_prov.is_running
    assert manager.current_state == WakeWordState.WAKE_LISTENING

    await manager.stop()
    assert not wake_prov.is_running


@pytest.mark.asyncio
async def test_wake_error_recovery():
    """Verify provider error does not crash the manager and recovers to WAKE_LISTENING."""
    wake_prov = MockWakeWordProvider(wake_word="jarvis")
    wake_prov.should_fail = RuntimeError("Simulated microphone driver crash")

    manager = WakeWordManager(provider=wake_prov)
    await manager.start()

    detected = await manager.wait_for_wake_word(timeout_sec=0.01)
    assert not detected
    # Should recover gracefully to WAKE_LISTENING
    assert manager.current_state == WakeWordState.WAKE_LISTENING

    await manager.stop()


@pytest.mark.asyncio
async def test_listen_loop_max_iterations():
    """Verify continuous listen loop executes target iterations and stops cleanly."""
    wake_prov = MockWakeWordProvider(wake_word="jarvis", trigger_after_calls=1)
    mock_conv = MagicMock(spec=VoiceConversationManager)
    mock_conv.run_once = AsyncMock(return_value={"transcript": "test", "response": "ok"})
    mock_tts = MagicMock(spec=TTSManager)
    mock_tts.speak = AsyncMock()

    manager = WakeWordManager(
        provider=wake_prov,
        conversation_manager=mock_conv,
        tts=mock_tts,
        cooldown_sec=0.01,
        wake_response_enabled=False,
    )

    detected_counter = 0

    def on_detected():
        nonlocal detected_counter
        detected_counter += 1

    await manager.listen_loop(on_wake_detected=on_detected, max_iterations=2)

    assert detected_counter == 2
    assert mock_conv.run_once.await_count == 2
    assert manager.current_state == WakeWordState.IDLE


@pytest.mark.asyncio
async def test_battery_constraint_handling():
    """Verify wake word listening is paused when on battery and WAKE_WORD_ON_BATTERY is False."""
    wake_prov = MockWakeWordProvider(wake_word="jarvis")
    manager = WakeWordManager(provider=wake_prov)
    manager.on_battery_allowed = False

    with patch.object(
        state_manager,
        "get_system_metrics",
        return_value={"battery_plugged": False, "battery_percent": 45.0},
    ):
        allowed = manager._check_battery_allowed()
        assert not allowed

        # wait_for_wake_word should exit early without triggering
        detected = await manager.wait_for_wake_word(timeout_sec=0.01)
        assert not detected


@pytest.mark.asyncio
async def test_graceful_stop_and_cleanup():
    """Verify stop() properly releases resources and sets service status."""
    wake_prov = MockWakeWordProvider(wake_word="jarvis")
    manager = WakeWordManager(provider=wake_prov)

    await manager.start()
    assert state_manager.get_service_status("wake_word") == ServiceStatus.RUNNING

    await manager.stop()
    assert not manager.is_running
    assert manager.current_state == WakeWordState.IDLE
    assert state_manager.get_service_status("wake_word") == ServiceStatus.STOPPED
