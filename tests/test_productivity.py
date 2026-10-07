"""Pytest test suite for Phase 10: Productivity & Personal Task System."""

import asyncio
from datetime import datetime, timedelta
import pytest

from app.productivity.database import ProductivityDatabase
from app.productivity.manager import ProductivityManager
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
from app.productivity.notes import NoteManager
from app.productivity.reminders import ReminderManager, parse_natural_datetime
from app.productivity.scheduler import ProductivityScheduler
from app.productivity.tasks import TaskManager
from app.productivity.timers import TimerManager
from app.tools.intent import parse_tool_intent
from app.tools.registry import tool_registry


@pytest.fixture
def clean_db():
    """Create a temporary in-memory database."""
    return ProductivityDatabase(db_path=":memory:")


def test_task_creation_and_listing(clean_db):
    """Verify task creation with priorities and listing filters."""
    tasks = TaskManager(db=clean_db)

    t1 = tasks.create_task(title="High task", priority="HIGH")
    t2 = tasks.create_task(title="Low task", priority="LOW")
    t3 = tasks.create_task(title="Med task", priority="MEDIUM")

    assert t1.id is not None
    all_t = tasks.list_tasks()
    assert len(all_t) == 3
    assert all_t[0].priority == TaskPriority.HIGH

    high_only = tasks.list_tasks(priority="HIGH")
    assert len(high_only) == 1
    assert high_only[0].title == "High task"


def test_task_completion_and_deletion(clean_db):
    """Verify task completion and deletion by ID and title."""
    tasks = TaskManager(db=clean_db)

    t = tasks.create_task(title="Project Alpha Report")
    assert t.status == TaskStatus.TODO

    # Complete by title
    completed = tasks.complete_task_by_title("Alpha")
    assert completed is not None
    assert completed.status == TaskStatus.COMPLETED

    # Delete by ID
    assert tasks.delete_task(t.id) is True
    assert tasks.get_task(t.id) is None


def test_reminder_natural_parsing():
    """Verify natural language parsing for times and reminders."""
    base = datetime(2026, 10, 7, 10, 0, 0)

    # Relative minutes
    dt1, rec1, msg1 = parse_natural_datetime("Remind me in 15 minutes to call Bob", base_time=base)
    assert dt1 == base + timedelta(minutes=15)
    assert rec1 == RecurrenceRule.NONE
    assert "call Bob" in msg1

    # Explicit PM
    dt2, rec2, msg2 = parse_natural_datetime("Remind me at 5 PM to submit timesheet", base_time=base)
    assert dt2.hour == 17
    assert dt2.minute == 0

    # Daily recurring
    dt3, rec3, msg3 = parse_natural_datetime("Remind me every day at 9 AM to take vitamins", base_time=base)
    assert rec3 == RecurrenceRule.DAILY
    assert dt3.hour == 9


def test_reminder_lifecycle_and_recurrence(clean_db):
    """Verify reminder creation, triggering, and daily recurrence advancement."""
    rems = ReminderManager(db=clean_db)

    now_iso = datetime.now().isoformat()
    rem = rems.create_reminder(message="Daily meeting", trigger_at=now_iso, recurrence="DAILY")
    assert rem.id is not None
    assert rem.status == ReminderStatus.PENDING

    # Complete -> auto advances next day
    completed = rems.complete_reminder(rem.id)
    assert completed.status == ReminderStatus.COMPLETED

    all_rems = rems.list_reminders()
    assert len(all_rems) == 2
    assert all_rems[1].status == ReminderStatus.PENDING
    assert all_rems[1].recurrence == RecurrenceRule.DAILY


def test_notes_crud_and_search(clean_db):
    """Verify notebook entries and keyword search."""
    notes = NoteManager(db=clean_db)

    n = notes.create_note(title="Meeting", content="Discussed Tamil speech models", tags=["ai", "tamil"])
    assert n.id is not None
    assert "tamil" in n.tags

    # Search
    results = notes.search_notes("speech")
    assert len(results) == 1
    assert results[0].title == "Meeting"

    # Delete
    assert notes.delete_note(n.id) is True
    assert len(notes.list_notes()) == 0


def test_timers_lifecycle():
    """Verify in-memory timer creation, remaining seconds, and cancellation."""
    timers = TimerManager()

    t = timers.create_timer(duration_seconds=60.0, label="Pasta")
    assert t.id is not None
    assert t.status == TimerStatus.RUNNING
    assert 55.0 <= t.remaining_seconds <= 60.0

    # Cancel
    cancelled = timers.cancel_timer(t.id)
    assert cancelled is not None
    assert cancelled.status == TimerStatus.CANCELLED


def test_scheduler_startup_recovery(clean_db):
    """Verify scheduler startup recovery handles missed reminders."""
    rems = ReminderManager(db=clean_db)
    sched = ProductivityScheduler(db=clean_db, reminder_mgr=rems)

    past_iso = (datetime.now() - timedelta(minutes=5)).isoformat()
    rems.create_reminder(message="Missed 1", trigger_at=past_iso)
    rems.create_reminder(message="Missed 2", trigger_at=past_iso)

    report = sched.recover_on_startup()
    assert report["recovered_count"] == 2
    assert len(clean_db.get_due_reminders(datetime.now().isoformat())) == 0


def test_productivity_manager_facade(clean_db):
    """Verify high-level unified facade methods."""
    tasks = TaskManager(db=clean_db)
    rems = ReminderManager(db=clean_db)
    notes = NoteManager(db=clean_db)
    timers = TimerManager()
    sched = ProductivityScheduler(db=clean_db, reminder_mgr=rems)

    facade = ProductivityManager(db=clean_db, tasks=tasks, reminders=rems, notes=notes, timers=timers, scheduler=sched)

    # Task creation
    task = facade.create_task(title="Review PR")
    assert task["id"] is not None

    # Reminder creation
    rem = facade.create_reminder(message="Water plants in 20 minutes")
    assert rem["id"] is not None

    # Note creation
    note = facade.create_note(title="Idea", content="Lightweight AI")
    assert note["id"] is not None

    # Timer creation
    timer = facade.create_timer(duration_text="10 minutes", label="Focus")
    assert timer["duration_seconds"] == 600.0


def test_intent_parsing_productivity_commands():
    """Verify natural Tamil & English intents map to Phase 10 productivity tools."""
    queries = [
        ("Add a task to finish my PPT", "create_task"),
        ("What are my tasks today?", "list_tasks"),
        ("Mark PCB design as completed", "complete_task"),
        ("Delete the presentation task", "delete_task"),
        ("Delete all my tasks", "clear_all_tasks"),
        ("Remind me to submit the report at 6 PM", "create_reminder"),
        ("What reminders do I have?", "list_reminders"),
        ("Cancel my reminder", "cancel_reminder"),
        ("Take a note: buy Arduino components", "create_note"),
        ("Show my notes", "list_notes"),
        ("Search my notes for PCB", "search_notes"),
        ("Set a timer for 10 minutes", "create_timer"),
        ("Cancel my timer", "cancel_timer"),
        ("How much time is left?", "get_timer_status"),
        # Tamil & Tanglish
        ("PPT complete பண்ணணும், task add பண்ணு", "create_task"),
        ("இன்னைக்கு என்ன tasks இருக்கு?", "list_tasks"),
        ("நாளைக்கு PPT submit பண்ணணும், reminder வை", "create_reminder"),
        ("10 minutes timer வை", "create_timer"),
    ]

    for user_input, expected_tool in queries:
        call = parse_tool_intent(user_input)
        assert call is not None, f"Failed to match intent for: '{user_input}'"
        assert call.tool == expected_tool, f"Expected {expected_tool} for '{user_input}', got {call.tool}"


def test_productivity_tools_registration():
    """Verify all Phase 10 tools are registered in ToolRegistry with proper permissions."""
    expected_safe = [
        "create_task",
        "list_tasks",
        "complete_task",
        "create_reminder",
        "list_reminders",
        "create_note",
        "list_notes",
        "search_notes",
        "create_timer",
        "cancel_timer",
        "get_timer_status",
    ]
    expected_confirm = [
        "delete_task",
        "clear_all_tasks",
        "cancel_reminder",
        "clear_all_reminders",
        "delete_note",
        "clear_all_notes",
    ]

    for tool_name in expected_safe:
        entry = tool_registry.get(tool_name)
        assert entry is not None, f"Tool {tool_name} not registered"
        schema, handler = entry
        assert schema.permission.value.lower() == "safe", f"Tool {tool_name} should be SAFE"

    for tool_name in expected_confirm:
        entry = tool_registry.get(tool_name)
        assert entry is not None, f"Tool {tool_name} not registered"
        schema, handler = entry
        assert schema.permission.value.lower() == "confirmation", f"Tool {tool_name} should require confirmation"
