"""Notes API routes for myoneAI Web Dashboard (Phase 11).

Provides CRUD and search endpoints delegating to the Phase 10 Notes Manager.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.productivity.notes import note_manager
from web.api.auth import require_auth
from web.api.schemas import (
    APISuccessResponse,
    NoteCreateRequest,
    NoteResponse,
    NoteUpdateRequest,
)

logger = logging.getLogger("myoneAI.web.routes.notes")

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.get("", response_model=List[NoteResponse], dependencies=[Depends(require_auth)])
async def list_notes(
    q: Optional[str] = Query(None, description="Search query keyword"),
    limit: int = Query(default=50, ge=1, le=200),
) -> List[NoteResponse]:
    """List or search notes."""
    if q and q.strip():
        items = note_manager.search_notes(q.strip(), limit=limit)
    else:
        items = note_manager.list_notes(limit=limit)

    return [
        NoteResponse(
            id=n.id if n.id is not None else 0,
            title=n.title,
            content=n.content,
            tags=n.tags or [],
            created_at=n.created_at,
            updated_at=n.updated_at,
        )
        for n in items
    ]


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_auth)])
async def create_note(payload: NoteCreateRequest) -> NoteResponse:
    """Create a new note."""
    try:
        saved = note_manager.create_note(
            title=payload.title,
            content=payload.content,
            tags=payload.tags or [],
        )
        return NoteResponse(
            id=saved.id if saved.id is not None else 0,
            title=saved.title,
            content=saved.content,
            tags=saved.tags or [],
            created_at=saved.created_at,
            updated_at=saved.updated_at,
        )
    except Exception as exc:
        logger.error("Failed to create note: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "NOTE_CREATION_FAILED",
                    "message": str(exc),
                },
            },
        )


@router.patch("/{note_id}", response_model=NoteResponse, dependencies=[Depends(require_auth)])
async def update_note(note_id: int, payload: NoteUpdateRequest) -> NoteResponse:
    """Update title, content, or tags of an existing note."""
    updated = note_manager.update_note(
        note_id=note_id,
        title=payload.title,
        content=payload.content,
        tags=payload.tags,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "NOTE_NOT_FOUND",
                    "message": f"Note #{note_id} not found.",
                },
            },
        )
    return NoteResponse(
        id=updated.id if updated.id is not None else note_id,
        title=updated.title,
        content=updated.content,
        tags=updated.tags or [],
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete("/{note_id}", response_model=APISuccessResponse, dependencies=[Depends(require_auth)])
async def delete_note(note_id: int) -> APISuccessResponse:
    """Delete a note by ID."""
    deleted = note_manager.delete_note(note_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "NOTE_NOT_FOUND",
                    "message": f"Note #{note_id} not found.",
                },
            },
        )
    return APISuccessResponse(success=True, message=f"Note #{note_id} deleted successfully.")
