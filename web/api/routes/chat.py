"""Text Chat API routes for myoneAI Web Dashboard (Phase 11).

Delegates conversational reasoning to the existing ConversationManager without duplicating AI logic.
"""

from datetime import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.ai.manager import conversation_manager
from app.core.config import Settings, get_settings
from web.api.auth import require_auth
from web.api.limiter import chat_limiter
from web.api.schemas import ChatRequest, ChatResponse

logger = logging.getLogger("myoneAI.web.routes.chat")

router = APIRouter(prefix="/chat", tags=["AI Chat"])


@router.post("", response_model=ChatResponse, dependencies=[Depends(require_auth)])
async def chat_with_assistant(
    request: Request,
    payload: ChatRequest,
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    """Process a typed conversational turn with Tamil JARVIS."""
    # Apply rate limiting
    chat_limiter.check(request)

    # Validate message length against configured limit
    max_len = settings.web_chat_max_length
    if len(payload.message) > max_len:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "MESSAGE_TOO_LONG",
                    "message": f"Message exceeds maximum allowed length of {max_len} characters.",
                },
            },
        )

    try:
        reply_text = await conversation_manager.respond(payload.message)
        return ChatResponse(
            success=True,
            response=reply_text,
            timestamp=datetime.now().isoformat(),
        )
    except Exception as exc:
        logger.error("Error during web chat processing: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "CHAT_PROCESSING_ERROR",
                    "message": "Failed to process chat message.",
                },
            },
        )
