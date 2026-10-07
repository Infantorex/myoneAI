"""Reminders API routes for myoneAI Web Dashboard (Phase 11).

Provides scheduling and listing endpoints delegating to the Phase 10 scheduler.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.productivity.reminders import reminder_manager
from web.api.auth import require_auth
from web.api.schemas import (
    APISuccessResponse,
    ReminderCreateRequest,
    ReminderResponse,
)

logger = logging.getLogger("myoneAI.web.routes.reminders")

router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.get("", response_model=List[ReminderResponse], dependencies=[Depends(require_auth)])
async def list_reminders(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (PENDING, TRIGGERED, CANCELLED, MISSED)"),
    limit: int = Query(default=50, ge=1, le=200),
) -> List[ReminderResponse]:
    """List scheduled and past reminders."""
    items = reminder_manager.list_reminders(status=status_filter, limit=limit)
    return [
        ReminderResponse(
            id=r.id if r.id is not None else 0,
            message=r.message,
            trigger_at=r.trigger_at,
            status=r.status.value if hasattr(r.status, "value") else str(r.status),
            recurrence=r.recurrence.value if hasattr(r.recurrence, "value") else str(r.recurrence),
            created_at=r.created_at,
        )
        for r in items
    ]


@router.post("", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_auth)])
async def create_reminder(payload: ReminderCreateRequest) -> ReminderResponse:
    """Create and schedule a new reminder."""
    try:
        saved = reminder_manager.create_reminder(
            message=payload.message,
            trigger_at=payload.trigger_at,
            recurrence=payload.recurrence or "NONE",
        )
        return ReminderResponse(
            id=saved.id if saved.id is not None else 0,
            message=saved.message,
            trigger_at=saved.trigger_at,
            status=saved.status.value if hasattr(saved.status, "value") else str(saved.status),
            recurrence=saved.recurrence.value if hasattr(saved.recurrence, "value") else str(saved.recurrence),
            created_at=saved.created_at,
        )
    except Exception as exc:
        logger.error("Failed to create reminder: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "REMINDER_CREATION_FAILED",
                    "message": str(exc),
                },
            },
        )


@router.delete("/{reminder_id}", response_model=APISuccessResponse, dependencies=[Depends(require_auth)])
async def delete_reminder(reminder_id: int) -> APISuccessResponse:
    """Cancel or delete a scheduled reminder by ID."""
    deleted = reminder_manager.delete_reminder(reminder_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "REMINDER_NOT_FOUND",
                    "message": f"Reminder #{reminder_id} not found.",
                },
            },
        )
    return APISuccessResponse(success=True, message=f"Reminder #{reminder_id} removed successfully.")
