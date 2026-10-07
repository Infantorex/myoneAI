"""Productivity & Personal Task System module for myoneAI / Tamil JARVIS (Phase 10).

Provides:
- SQLite persistent storage for Tasks, Reminders, and Notes.
- Low-power periodic scheduler with startup recovery and recurrence support.
- In-memory countdown timers.
- Natural date/time and speech intent parsing.
- Zero external server dependencies (Redis/Celery/MongoDB).
"""

from app.productivity.database import ProductivityDatabase, productivity_db
from app.productivity.manager import ProductivityManager, productivity_manager
from app.productivity.models import (
    ActiveTimer,
    NoteItem,
    RecurrenceRule,
    ReminderItem,
    ReminderStatus,
    TaskItem,
    TaskPriority,
    TaskStatus,
    TimerStatus,
)
from app.productivity.notes import NoteManager, note_manager
from app.productivity.reminders import ReminderManager, parse_natural_datetime, reminder_manager
from app.productivity.scheduler import ProductivityScheduler, productivity_scheduler
from app.productivity.tasks import TaskManager, task_manager
from app.productivity.timers import TimerManager, timer_manager

__all__ = [
    # Models & Enums
    "TaskPriority",
    "TaskStatus",
    "ReminderStatus",
    "RecurrenceRule",
    "TimerStatus",
    "TaskItem",
    "ReminderItem",
    "NoteItem",
    "ActiveTimer",
    # Utilities
    "parse_natural_datetime",
    # Managers & Engines
    "ProductivityDatabase",
    "productivity_db",
    "TaskManager",
    "task_manager",
    "ReminderManager",
    "reminder_manager",
    "NoteManager",
    "note_manager",
    "TimerManager",
    "timer_manager",
    "ProductivityScheduler",
    "productivity_scheduler",
    "ProductivityManager",
    "productivity_manager",
]
