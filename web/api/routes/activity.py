"""Activity feed API routes for myoneAI Web Dashboard (Phase 11).

Provides read-only access to sanitized assistant activity events.
"""

from typing import List
from fastapi import APIRouter, Depends, Query

from web.api.activity_tracker import activity_tracker
from web.api.auth import require_auth
from web.api.schemas import ActivityEventResponse

router = APIRouter(prefix="/activity", tags=["Activity Feed"])


@router.get("", response_model=List[ActivityEventResponse], dependencies=[Depends(require_auth)])
async def get_recent_activity(
    limit: int = Query(default=30, ge=1, le=100),
) -> List[ActivityEventResponse]:
    """Retrieve recent sanitized activity items (no secrets or sensitive data)."""
    events = activity_tracker.get_events(limit=limit)
    return [
        ActivityEventResponse(
            id=e.get("id"),
            timestamp=e.get("timestamp", ""),
            event_type=e.get("event_type", "INFO"),
            description=e.get("description", ""),
            level=e.get("level", "INFO"),
        )
        for e in events
    ]
