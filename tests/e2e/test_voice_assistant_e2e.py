"""End-to-End Test: Wake Word -> Speech Detection -> STT -> AI -> Memory/Tool -> TTS -> Speaker."""

import asyncio
import pytest

from app.ai.manager import ConversationManager
from app.ai.provider import MockAIProvider
from app.core.memory.manager import MemoryManager
from app.core.state import AssistantState, StateManager
from app.security.permissions import PermissionManager
from app.tools.executor import ToolExecutor
from app.voice.audio import AudioPlayer
from app.voice.stt import MockSTTProvider
from app.voice.tts import MockTTSProvider
from app.voice.vad import VoiceActivityDetector, VADState
from app.voice.wakeword_provider import MockWakeWordProvider
from tests.fixtures.audio_fixtures import generate_synthetic_pcm


@pytest.mark.asyncio
async def test_complete_voice_assistant_e2e_cycle(tmp_path):
    """Verify complete end-to-end hands-free assistant execution pipeline."""
    # 1. Environment & State Setup
    state_mgr = StateManager()
    assert state_mgr.current_state == AssistantState.IDLE

    mem_db = tmp_path / "e2e_memory.db"
    mem_mgr = MemoryManager(db_path=mem_db)
    pm = PermissionManager()
    executor = ToolExecutor(permissions=pm)
    ai = ConversationManager(
        provider=MockAIProvider(default_response="சிஸ்டம் நிலை சீராக உள்ளது."),
        memory=mem_mgr,
        tools=executor,
        permissions=pm,
    )
    stt = MockSTTProvider(default_response="check battery")
    tts = MockTTSProvider()
    wakeword = MockWakeWordProvider()

    # 2. Wake Word Detection Trigger
    detected = await wakeword.detect()
    assert detected is True
    state_mgr.set_state(AssistantState.LISTENING)

    # 3. Speech Capture & VAD
    vad = VoiceActivityDetector()
    pcm_audio = generate_synthetic_pcm(duration_sec=0.2, amplitude=15000)
    vad_state = vad.process_chunk(pcm_audio)
    assert vad_state == VADState.SPEECH_DETECTED

    # 4. Speech Recognition (STT)
    state_mgr.set_state(AssistantState.PROCESSING)
    stt_res = await stt.transcribe(pcm_audio)
    assert stt_res.text == "check battery"

    # 5. AI Reasoning, Memory, & Tool Execution
    ai_reply = await ai.respond(stt_res.text)
    assert ai_reply is not None
    assert len(ai_reply) > 0

    # 6. Speech Synthesis (TTS)
    state_mgr.set_state(AssistantState.SPEAKING)
    tts_res = await tts.synthesize(ai_reply)
    assert len(tts_res.audio_bytes) > 0

    # 7. Safe Return to IDLE
    state_mgr.set_state(AssistantState.IDLE)
    assert state_mgr.current_state == AssistantState.IDLE
