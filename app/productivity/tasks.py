"""Task management business logic and helpers (Phase 10)."""

import logging
from typing import Any, Dict, List, Optional

from app.productivity.database import ProductivityDatabase, productivity_db
from app.productivity.models import TaskItem, TaskPriority, TaskStatus

logger = logging.getLogger("myoneAI.productivity.tasks")


class TaskManager:
    """Manages user tasks, priorities, and status lifecycles."""

    def __init__(self, db: Optional[ProductivityDatabase] = None) -> None:
        self.db = db or productivity_db

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "MEDIUM",
        due_at: Optional[str] = None,
    ) -> TaskItem:
        """Create and store a new user task."""
        if not title or not title.strip():
            raise ValueError("Task title cannot be empty.")

        try:
            p_enum = TaskPriority(priority.upper())
        except Exception:
            p_enum = TaskPriority.MEDIUM

        item = TaskItem(
            title=title.strip(),
            description=description.strip(),
            priority=p_enum,
            status=TaskStatus.TODO,
            due_at=due_at,
        )
        saved = self.db.add_task(item)
        logger.info("Created Task #%s: '%s' (Priority: %s)", saved.id, saved.title, saved.priority.value)
        return saved

    def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 20,
    ) -> List[TaskItem]:
        """List tasks matching optional status or priority."""
        s_enum = None
        if status:
            try:
                s_enum = TaskStatus(status.upper())
            except Exception:
                pass

        p_enum = None
        if priority:
            try:
                p_enum = TaskPriority(priority.upper())
            except Exception:
                pass

        return self.db.list_tasks(status=s_enum, priority=p_enum, limit=limit)

    def get_task(self, task_id: int) -> Optional[TaskItem]:
        """Retrieve task by numeric ID."""
        return self.db.get_task(task_id)

    def search_tasks(self, query: str, limit: int = 10) -> List[TaskItem]:
        """Search tasks by title or description keyword."""
        if not query or not query.strip():
            return []
        return self.db.search_tasks(query.strip(), limit=limit)

    def update_task(
        self,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        due_at: Optional[str] = None,
    ) -> Optional[TaskItem]:
        """Update fields of an existing task."""
        p_enum = None
        if priority:
            try:
                p_enum = TaskPriority(priority.upper())
            except Exception:
                pass

        s_enum = None
        if status:
            try:
                s_enum = TaskStatus(status.upper())
            except Exception:
                pass

        return self.db.update_task(
            task_id=task_id,
            title=title,
            description=description,
            priority=p_enum,
            status=s_enum,
            due_at=due_at,
        )

    def complete_task(self, task_id: int) -> Optional[TaskItem]:
        """Mark task as COMPLETED by ID."""
        return self.db.complete_task(task_id)

    def complete_task_by_title(self, title_query: str) -> Optional[TaskItem]:
        """Find the closest matching active task by title and mark it as COMPLETED."""
        matches = self.search_tasks(title_query, limit=5)
        # Filter for TODO or IN_PROGRESS
        active = [t for t in matches if t.status in (TaskStatus.TODO, TaskStatus.IN_PROGRESS)]
        target = active[0] if active else (matches[0] if matches else None)
        if target and target.id is not None:
            return self.db.complete_task(target.id)
        return None

    def delete_task(self, task_id: int) -> bool:
        """Delete task by ID."""
        return self.db.delete_task(task_id)

    def delete_task_by_title(self, title_query: str) -> Optional[TaskItem]:
        """Find matching task by title and delete it."""
        matches = self.search_tasks(title_query, limit=1)
        if matches and matches[0].id is not None:
            deleted = self.db.delete_task(matches[0].id)
            if deleted:
                return matches[0]
        return None

    def clear_all_tasks(self) -> int:
        """Clear all tasks."""
        return self.db.clear_all_tasks()


# Global TaskManager singleton
task_manager = TaskManager()
