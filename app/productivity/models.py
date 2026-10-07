"""Data models and schemas for the Productivity & Personal Task System (Phase 10)."""

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskPriority(str, Enum):
    """Priority levels for user tasks."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TaskStatus(str, Enum):
    """Lifecycle status for user tasks."""
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ReminderStatus(str, Enum):
    """Lifecycle status for scheduled reminders."""
    PENDING = "PENDING"
    TRIGGERED = "TRIGGERED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class RecurrenceRule(str, Enum):
    """Recurrence frequency for repetitive reminders."""
    NONE = "NONE"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"


class TimerStatus(str, Enum):
    """State of an in-memory countdown timer."""
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass
class TaskItem:
    """Represents a structured user task."""
    title: str
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    due_at: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value if isinstance(self.priority, TaskPriority) else str(self.priority),
            "status": self.status.value if isinstance(self.status, TaskStatus) else str(self.status),
            "due_at": self.due_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ReminderItem:
    """Represents a scheduled notification or reminder."""
    message: str
    trigger_at: str
    status: ReminderStatus = ReminderStatus.PENDING
    recurrence: RecurrenceRule = RecurrenceRule.NONE
    id: Optional[int] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "message": self.message,
            "trigger_at": self.trigger_at,
            "status": self.status.value if isinstance(self.status, ReminderStatus) else str(self.status),
            "recurrence": self.recurrence.value if isinstance(self.recurrence, RecurrenceRule) else str(self.recurrence),
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


@dataclass
class NoteItem:
    """Represents a persistent user notebook entry."""
    title: str
    content: str
    tags: List[str] = field(default_factory=list)
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ActiveTimer:
    """Represents an active local in-memory countdown timer."""
    id: str
    label: str
    duration_seconds: float
    start_time: float
    end_time: float
    status: TimerStatus = TimerStatus.RUNNING

    @property
    def remaining_seconds(self) -> float:
        """Calculate remaining time until expiration in seconds."""
        if self.status != TimerStatus.RUNNING:
            return 0.0
        now = time.time()
        return max(0.0, self.end_time - now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "duration_seconds": self.duration_seconds,
            "remaining_seconds": round(self.remaining_seconds, 1),
            "status": self.status.value if isinstance(self.status, TimerStatus) else str(self.status),
            "start_time": self.start_time,
            "end_time": self.end_time,
        }
