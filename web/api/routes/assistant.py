"""Assistant state and control routes for myoneAI Web Dashboard (Phase 11).

Provides lifecycle status and safe control endpoints without bypassing security policies.
"""

import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.state import AssistantState, state_manager
from web.api.auth import require_auth
from web.api.schemas import (
    AssistantControlRequest,
    AssistantStatusResponse,
)

logger = logging.getLogger("myoneAI.web.routes.assistant")

router = APIRouter(prefix="/assistant", tags=["Assistant Status & Control"])


def map_assistant_state(raw_state: str) -> str:
    """Map internal state enum to canonical allowed dashboard states: idle, listening, thinking, speaking, error."""
    s = raw_state.lower()
    if s in ("listening",):
        return "listening"
    elif s in ("processing", "thinking"):
        return "thinking"
    elif s in ("speaking",):
        return "speaking"
    elif s in ("error",):
        return "error"
    return "idle"


@router.get("/status", response_model=AssistantStatusResponse, dependencies=[Depends(require_auth)])
async def get_assistant_status(settings: Settings = Depends(get_settings)) -> AssistantStatusResponse:
    """Retrieve current JARVIS execution state and capabilities."""
    raw_state = state_manager.current_state.value
    mapped_state = map_assistant_state(raw_state)

    wake_word_enabled = getattr(settings, "wake_word_enabled", True)
    voice_enabled = getattr(settings, "voice_loop_enabled", True)

    return AssistantStatusResponse(
        state=mapped_state,
        wake_word_enabled=wake_word_enabled,
        voice_enabled=voice_enabled,
        uptime_seconds=round(state_manager.uptime_seconds, 1),
    )


@router.post("/start", dependencies=[Depends(require_auth)])
async def start_assistant() -> Dict[str, Any]:
    """Activate assistant voice / listening mode."""
    logger.info("Web request to start assistant received.")
    state_manager.set_state(AssistantState.LISTENING, context={"triggered_by": "web_dashboard"})
    return {
        "success": True,
        "message": "Assistant listening mode activated.",
        "state": "listening",
    }


@router.post("/stop", dependencies=[Depends(require_auth)])
async def stop_assistant() -> Dict[str, Any]:
    """Deactivate/idle assistant voice mode."""
    logger.info("Web request to stop assistant received.")
    state_manager.set_state(AssistantState.IDLE, context={"triggered_by": "web_dashboard"})
    return {
        "success": True,
        "message": "Assistant returned to idle state.",
        "state": "idle",
    }
