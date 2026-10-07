"""Memory management API routes for myoneAI Web Dashboard (Phase 11).

Provides read/write/delete operations for controlled AI memory with privacy safeguards.
"""

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.memory.manager import memory_manager
from app.core.memory.privacy import SensitiveDataMemoryError
from web.api.auth import require_auth
from web.api.schemas import (
    APISuccessResponse,
    MemoryClearRequest,
    MemoryCreateRequest,
    MemoryItemResponse,
    MemoryStatsResponse,
)

logger = logging.getLogger("myoneAI.web.routes.memory")

router = APIRouter(prefix="/memory", tags=["AI Memory"])


@router.get("", response_model=List[MemoryItemResponse], dependencies=[Depends(require_auth)])
async def list_memories(
    q: Optional[str] = Query(None, description="Search keyword query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(default=100, ge=1, le=500),
) -> List[MemoryItemResponse]:
    """List stored memory entries for the dashboard."""
    if q and q.strip():
        items = await memory_manager.search(q.strip(), limit=limit, category=category)
    else:
        items = await memory_manager.list_all(limit=limit, category=category)

    res: List[MemoryItemResponse] = []
    for m in items:
        updated_dt = datetime.fromtimestamp(m.updated_at).isoformat() if hasattr(m, "updated_at") and m.updated_at else datetime.now().isoformat()
        created_dt = datetime.fromtimestamp(m.created_at).isoformat() if hasattr(m, "created_at") and m.created_at else None
        res.append(MemoryItemResponse(
            id=m.id,
            category=m.category,
            key=m.key,
            value=m.value,
            confidence=m.confidence,
            updated=updated_dt,
            created_at=created_dt,
        ))
    return res


@router.get("/stats", response_model=MemoryStatsResponse, dependencies=[Depends(require_auth)])
async def get_memory_stats() -> MemoryStatsResponse:
    """Return memory count and category summary."""
    items = await memory_manager.list_all(limit=1000)
    cat_counts: Dict[str, int] = {}
    for item in items:
        cat = item.category
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    return MemoryStatsResponse(
        total_memories=len(items),
        categories=cat_counts,
    )


@router.post("", response_model=MemoryItemResponse, dependencies=[Depends(require_auth)])
async def create_memory(payload: MemoryCreateRequest) -> MemoryItemResponse:
    """Store a new preference or factual memory item."""
    try:
        saved = await memory_manager.remember(
            category=payload.category,
            key=payload.key,
            value=payload.value,
        )
        updated_dt = datetime.fromtimestamp(saved.updated_at).isoformat() if hasattr(saved, "updated_at") and saved.updated_at else datetime.now().isoformat()
        return MemoryItemResponse(
            id=saved.id,
            category=saved.category,
            key=saved.key,
            value=saved.value,
            confidence=saved.confidence,
            updated=updated_dt,
        )
    except SensitiveDataMemoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "PRIVACY_VIOLATION",
                    "message": str(exc),
                },
            },
        )
    except Exception as exc:
        logger.error("Error saving memory: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "MEMORY_SAVE_FAILED",
                    "message": "Failed to save memory item.",
                },
            },
        )


@router.delete("/{memory_id}", response_model=APISuccessResponse, dependencies=[Depends(require_auth)])
async def delete_memory_by_id(memory_id: str) -> APISuccessResponse:
    """Delete an individual memory record by ID."""
    deleted = await memory_manager.delete(item_id=memory_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Memory item '{memory_id}' not found.",
                },
            },
        )
    return APISuccessResponse(success=True, message=f"Memory '{memory_id}' deleted successfully.")


@router.delete("", response_model=APISuccessResponse, dependencies=[Depends(require_auth)])
async def clear_all_memories(
    confirmed: bool = Query(default=False, description="Must be true to confirm deletion"),
) -> APISuccessResponse:
    """Clear all stored memories. Requires explicit confirmation."""
    if not confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "CONFIRMATION_REQUIRED",
                    "message": "Are you sure you want to delete all saved memories? Set confirmed=true to proceed.",
                },
            },
        )

    count = memory_manager.store.clear_all()
    return APISuccessResponse(
        success=True,
        message=f"Cleared {count} memory records.",
    )
