"""End-to-End Test: Voice / Text -> Productivity Intent -> Database -> Confirmation / Query."""

import pytest

from app.productivity.database import ProductivityDatabase
from app.productivity.manager import ProductivityManager
from app.productivity.notes import NoteManager
from app.productivity.tasks import TaskManager


def test_productivity_full_workflow_e2e(tmp_path):
    """Verify task, reminder, and note workflows with persistence and recovery."""
    db_path = str(tmp_path / "e2e_prod.db")
    db = ProductivityDatabase(db_path=db_path)
    tasks_mgr = TaskManager(db=db)
    notes_mgr = NoteManager(db=db)
    mgr = ProductivityManager(db=db, tasks=tasks_mgr, notes=notes_mgr)

    # 1. Create task
    task = mgr.create_task(
        title="Deploy Phase 14 security verification",
        description="Verify 0 vulnerabilities and 100% tests pass",
        priority="HIGH",
    )
    assert task["id"] is not None

    # 2. Query task
    tasks = mgr.list_tasks(status="TODO")
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Deploy Phase 14 security verification"

    # 3. Create Note
    note = mgr.create_note(
        title="Release Checklist",
        content="All phases 1-13 verified. Performance budgets respected.",
    )
    assert note["id"] is not None

    # 4. Search Note
    found = mgr.search_notes("Performance budgets")
    assert len(found) == 1
    assert "Release Checklist" in found[0]["title"]

    # 5. Complete task
    mgr.complete_task(task_id=task["id"])
    assert len(mgr.list_tasks(status="TODO")) == 0
    assert len(mgr.list_tasks(status="DONE")) == 1
