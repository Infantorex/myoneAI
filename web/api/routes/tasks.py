"""Task management API routes for myoneAI Web Dashboard (Phase 11).

Provides CRUD endpoints for personal tasks delegating to the Phase 10 productivity system.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.productivity.tasks import task_manager
from web.api.auth import require_auth
from web.api.schemas import (
    APISuccessResponse,
    TaskCreateRequest,
    TaskResponse,
    TaskUpdateRequest,
)

logger = logging.getLogger("myoneAI.web.routes.tasks")

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=List[TaskResponse], dependencies=[Depends(require_auth)])
async def list_tasks(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (TODO, IN_PROGRESS, COMPLETED, CANCELLED)"),
    priority_filter: Optional[str] = Query(None, alias="priority", description="Filter by priority (LOW, MEDIUM, HIGH, CRITICAL)"),
    limit: int = Query(default=50, ge=1, le=200),
) -> List[TaskResponse]:
    """List tasks matching optional status and priority filters."""
    items = task_manager.list_tasks(status=status_filter, priority=priority_filter, limit=limit)
    return [
        TaskResponse(
            id=t.id if t.id is not None else 0,
            title=t.title,
            description=t.description,
            priority=t.priority.value if hasattr(t.priority, "value") else str(t.priority),
            status=t.status.value if hasattr(t.status, "value") else str(t.status),
            due_at=t.due_at,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in items
    ]


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_auth)])
async def create_task(payload: TaskCreateRequest) -> TaskResponse:
    """Create a new task."""
    try:
        saved = task_manager.create_task(
            title=payload.title,
            description=payload.description or "",
            priority=payload.priority or "MEDIUM",
            due_at=payload.due_at,
        )
        return TaskResponse(
            id=saved.id if saved.id is not None else 0,
            title=saved.title,
            description=saved.description,
            priority=saved.priority.value if hasattr(saved.priority, "value") else str(saved.priority),
            status=saved.status.value if hasattr(saved.status, "value") else str(saved.status),
            due_at=saved.due_at,
            created_at=saved.created_at,
            updated_at=saved.updated_at,
        )
    except Exception as exc:
        logger.error("Failed to create task: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "TASK_CREATION_FAILED",
                    "message": str(exc),
                },
            },
        )


@router.patch("/{task_id}", response_model=TaskResponse, dependencies=[Depends(require_auth)])
async def update_task(task_id: int, payload: TaskUpdateRequest) -> TaskResponse:
    """Update fields or status of an existing task."""
    updated = task_manager.update_task(
        task_id=task_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        status=payload.status,
        due_at=payload.due_at,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "TASK_NOT_FOUND",
                    "message": f"Task #{task_id} not found.",
                },
            },
        )
    return TaskResponse(
        id=updated.id if updated.id is not None else task_id,
        title=updated.title,
        description=updated.description,
        priority=updated.priority.value if hasattr(updated.priority, "value") else str(updated.priority),
        status=updated.status.value if hasattr(updated.status, "value") else str(updated.status),
        due_at=updated.due_at,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete("/{task_id}", response_model=APISuccessResponse, dependencies=[Depends(require_auth)])
async def delete_task(task_id: int) -> APISuccessResponse:
    """Delete a task by ID."""
    deleted = task_manager.delete_task(task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "TASK_NOT_FOUND",
                    "message": f"Task #{task_id} not found.",
                },
            },
        )
    return APISuccessResponse(success=True, message=f"Task #{task_id} deleted successfully.")
