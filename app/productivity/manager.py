"""Central unified manager orchestrating tasks, reminders, notes, and timers (Phase 10)."""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from app.core.config import Settings, get_settings
from app.productivity.database import ProductivityDatabase, productivity_db
from app.productivity.models import (
    ActiveTimer,
    NoteItem,
    RecurrenceRule,
    ReminderItem,
    ReminderStatus,
    TaskItem,
    TaskPriority,
    TaskStatus,
)
from app.productivity.notes import NoteManager, note_manager
from app.productivity.reminders import ReminderManager, parse_natural_datetime, reminder_manager
from app.productivity.scheduler import ProductivityScheduler, productivity_scheduler
from app.productivity.tasks import TaskManager, task_manager
from app.productivity.timers import TimerManager, timer_manager

logger = logging.getLogger("myoneAI.productivity.manager")


class ProductivityManager:
    """Central facade orchestrating productivity subsystems for AI and voice turns."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        db: Optional[ProductivityDatabase] = None,
        tasks: Optional[TaskManager] = None,
        reminders: Optional[ReminderManager] = None,
        notes: Optional[NoteManager] = None,
        timers: Optional[TimerManager] = None,
        scheduler: Optional[ProductivityScheduler] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.db = db or productivity_db
        self.tasks = tasks or task_manager
        self.reminders = reminders or reminder_manager
        self.notes = notes or note_manager
        self.timers = timers or timer_manager
        self.scheduler = scheduler or productivity_scheduler

    # --------------------------------------------------------------------------
    # Task Methods
    # --------------------------------------------------------------------------

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "MEDIUM",
        due_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new task."""
        # Check if due_at is specified in title via natural language
        if not due_at:
            dt, _, clean_title = parse_natural_datetime(title)
            if dt:
                due_at = dt.isoformat()
                title = clean_title or title

        item = self.tasks.create_task(
            title=title,
            description=description,
            priority=priority,
            due_at=due_at,
        )
        return item.to_dict()

    def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """List user tasks."""
        items = self.tasks.list_tasks(status=status, priority=priority, limit=limit)
        return [item.to_dict() for item in items]

    def complete_task(
        self,
        task_id: Optional[int] = None,
        title: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Mark task as complete by ID or title query."""
        if task_id is not None:
            item = self.tasks.complete_task(task_id)
        elif title:
            item = self.tasks.complete_task_by_title(title)
        else:
            return None
        return item.to_dict() if item else None

    def delete_task(
        self,
        task_id: Optional[int] = None,
        title: Optional[str] = None,
    ) -> bool:
        """Delete task by ID or title."""
        if task_id is not None:
            return self.tasks.delete_task(task_id)
        elif title:
            item = self.tasks.delete_task_by_title(title)
            return item is not None
        return False

    def search_tasks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search tasks by keyword."""
        items = self.tasks.search_tasks(query, limit=limit)
        return [item.to_dict() for item in items]

    # --------------------------------------------------------------------------
    # Reminder Methods
    # --------------------------------------------------------------------------

    def create_reminder(
        self,
        message: str,
        trigger_at: Optional[str] = None,
        recurrence: str = "NONE",
    ) -> Dict[str, Any]:
        """Schedule a reminder, parsing natural time expressions if trigger_at is missing."""
        if not trigger_at:
            dt, rec_rule, clean_msg = parse_natural_datetime(message)
            if dt:
                trigger_at = dt.isoformat()
                message = clean_msg or message
                if recurrence == "NONE" and rec_rule != RecurrenceRule.NONE:
                    recurrence = rec_rule.value
            else:
                # Default to 30 minutes from now if no time was detected
                trigger_at = (datetime.now() + timedelta(minutes=30)).isoformat()

        item = self.reminders.create_reminder(
            message=message,
            trigger_at=trigger_at,
            recurrence=recurrence,
        )
        return item.to_dict()

    def list_reminders(
        self,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """List reminders."""
        items = self.reminders.list_reminders(status=status, limit=limit)
        return [item.to_dict() for item in items]

    def cancel_reminder(
        self,
        reminder_id: Optional[int] = None,
        message: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Cancel a reminder by ID or message match."""
        if reminder_id is not None:
            item = self.reminders.cancel_reminder(reminder_id)
        elif message:
            item = self.reminders.cancel_reminder_by_message(message)
        else:
            return None
        return item.to_dict() if item else None

    # --------------------------------------------------------------------------
    # Note Methods
    # --------------------------------------------------------------------------

    def create_note(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a user note."""
        item = self.notes.create_note(title=title, content=content, tags=tags)
        return item.to_dict()

    def list_notes(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recently updated notes."""
        items = self.notes.list_notes(limit=limit)
        return [item.to_dict() for item in items]

    def search_notes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search notes by keyword."""
        items = self.notes.search_notes(query, limit=limit)
        return [item.to_dict() for item in items]

    def delete_note(
        self,
        note_id: Optional[int] = None,
        title: Optional[str] = None,
    ) -> bool:
        """Delete note by ID or title."""
        if note_id is not None:
            return self.notes.delete_note(note_id)
        elif title:
            item = self.notes.delete_note_by_title(title)
            return item is not None
        return False

    # --------------------------------------------------------------------------
    # Timer Methods
    # --------------------------------------------------------------------------

    def create_timer(
        self,
        duration_seconds: Optional[float] = None,
        duration_text: Optional[str] = None,
        label: str = "Timer",
    ) -> Dict[str, Any]:
        """Create and start an in-memory countdown timer."""
        secs = duration_seconds
        if secs is None and duration_text:
            secs = self._parse_timer_duration(duration_text)

        if not secs or secs <= 0:
            secs = 600.0  # Default 10 minutes

        timer = self.timers.create_timer(duration_seconds=secs, label=label)
        return timer.to_dict()

    def get_timer_status(self, timer_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get status of running timer."""
        if timer_id:
            timer = self.timers.get_timer(timer_id)
        else:
            timer = self.timers.get_latest_timer()
        return timer.to_dict() if timer else None

    def cancel_timer(self, timer_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Cancel a running timer."""
        timer = self.timers.cancel_timer(timer_id)
        return timer.to_dict() if timer else None

    def list_active_timers(self) -> List[Dict[str, Any]]:
        """List all active running timers."""
        return [t.to_dict() for t in self.timers.get_active_timers()]

    # --------------------------------------------------------------------------
    # Bulk Deletion / Clear Methods (Requires Confirmation)
    # --------------------------------------------------------------------------

    def clear_all_tasks(self) -> int:
        """Delete all tasks."""
        return self.tasks.clear_all_tasks()

    def clear_all_reminders(self) -> int:
        """Delete all reminders."""
        return self.reminders.clear_all_reminders()

    def clear_all_notes(self) -> int:
        """Delete all notes."""
        return self.notes.clear_all_notes()

    def clear_all_productivity(self) -> Dict[str, int]:
        """Clear all tasks, reminders, and notes."""
        return {
            "tasks_deleted": self.clear_all_tasks(),
            "reminders_deleted": self.clear_all_reminders(),
            "notes_deleted": self.clear_all_notes(),
            "timers_cancelled": self.timers.clear_all_timers(),
        }

    def _parse_timer_duration(self, text: str) -> Optional[float]:
        """Helper to extract timer duration from string (e.g. '10 minutes', '30 seconds', '1 hour')."""
        match = re.search(r"(\d+(?:\.\d+)?)\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours|s|sec|secs|second|seconds)?", text.lower())
        if not match:
            return None
        val = float(match.group(1))
        unit = (match.group(2) or "m").lower()
        if unit.startswith("h"):
            return val * 3600.0
        elif unit.startswith("s"):
            return val
        else:
            return val * 60.0


# Global ProductivityManager singleton
productivity_manager = ProductivityManager()
