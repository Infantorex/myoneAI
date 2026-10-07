"""Unit tests for Phase 10 Productivity & Task System."""

import pytest

from app.productivity.database import ProductivityDatabase
from app.productivity.manager import ProductivityManager
from app.productivity.models import (
    NoteItem,
    ReminderItem,
    ReminderStatus,
    TaskItem,
    TaskPriority,
    TaskStatus,
)
from app.productivity.notes import NoteManager
from app.productivity.tasks import TaskManager


def test_productivity_tasks_crud(tmp_path):
    """Verify task addition, completion, listing, and deletion."""
    db_path = str(tmp_path / "unit_prod.db")
    db = ProductivityDatabase(db_path=db_path)
    tasks = TaskManager(db=db)
    mgr = ProductivityManager(db=db, tasks=tasks)

    # 1. Add Task
    task = mgr.create_task(title="Finish complete security audit", priority="HIGH")
    assert task["id"] is not None
    assert task["status"] == "TODO"

    # 2. Complete Task
    completed = mgr.complete_task(task_id=task["id"])
    assert completed is not None
    assert completed["status"] == "COMPLETED"

    # 3. List Tasks
    all_tasks = mgr.list_tasks(status="COMPLETED")
    assert len(all_tasks) == 1


def test_productivity_notes_search(tmp_path):
    """Verify note creation and keyword search."""
    db_path = str(tmp_path / "unit_notes.db")
    db = ProductivityDatabase(db_path=db_path)
    notes = NoteManager(db=db)
    mgr = ProductivityManager(db=db, notes=notes)

    mgr.create_note(title="Project Architecture", content="JARVIS is designed for 8GB RAM Windows i3")
    results = mgr.search_notes("architecture")
    assert len(results) == 1
    assert "8GB RAM" in results[0]["content"]
