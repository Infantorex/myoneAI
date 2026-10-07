"""Self-contained test and demonstration suite for Phase 10 Productivity & Tasks.

Can be run directly:
    python -m app.productivity.test_productivity
or via pytest.
"""

import asyncio
import time
from datetime import datetime, timedelta

from app.core.config import Settings
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


def test_task_crud():
    """Verify task creation, listing, updating, completing, and deletion."""
    db = ProductivityDatabase(db_path=":memory:")
    mgr = TaskManager(db=db)

    # 1. Create
    t1 = mgr.create_task(title="Finish PPT", priority="HIGH")
    assert t1.id is not None
    assert t1.title == "Finish PPT"
    assert t1.priority == TaskPriority.HIGH
    assert t1.status == TaskStatus.TODO

    t2 = mgr.create_task(title="Order PCB components", priority="MEDIUM")
    assert t2.id is not None

    # 2. List
    tasks = mgr.list_tasks()
    assert len(tasks) == 2
    # High priority should be first
    assert tasks[0].priority == TaskPriority.HIGH

    # 3. Search
    found = mgr.search_tasks("PCB")
    assert len(found) == 1
    assert found[0].title == "Order PCB components"

    # 4. Complete
    updated = mgr.complete_task(t1.id)
    assert updated is not None
    assert updated.status == TaskStatus.COMPLETED

    # 5. Delete
    deleted = mgr.delete_task(t2.id)
    assert deleted is True
    assert len(mgr.list_tasks()) == 1


def test_natural_datetime_parsing():
    """Verify relative and natural time expressions."""
    base = datetime(2026, 10, 7, 12, 0, 0)

    # Relative minutes
    dt1, rec1, msg1 = parse_natural_datetime("Remind me in 30 minutes to check prototype", base_time=base)
    assert dt1 == base + timedelta(minutes=30)
    assert rec1 == RecurrenceRule.NONE
    assert "check prototype" in msg1

    # Relative hours
    dt2, rec2, msg2 = parse_natural_datetime("in 2 hours call teammate", base_time=base)
    assert dt2 == base + timedelta(hours=2)

    # Explicit time PM
    dt3, rec3, msg3 = parse_natural_datetime("at 6 PM submit report", base_time=base)
    assert dt3 == datetime(2026, 10, 7, 18, 0, 0)
    assert "submit report" in msg3

    # Daily recurring
    dt4, rec4, msg4 = parse_natural_datetime("every day at 8 AM take vitamins", base_time=base)
    assert rec4 == RecurrenceRule.DAILY
    assert dt4.hour == 8

    # Tamil relative minutes
    dt5, rec5, msg5 = parse_natural_datetime("10 minutes-ல் prototype பார்", base_time=base)
    assert dt5 == base + timedelta(minutes=10)


def test_reminders_and_recurrence():
    """Verify reminder scheduling, triggering, and daily/weekly recurrence."""
    db = ProductivityDatabase(db_path=":memory:")
    rem_mgr = ReminderManager(db=db)

    # Create daily reminder
    trigger_iso = (datetime.now() + timedelta(seconds=1)).isoformat()
    rem = rem_mgr.create_reminder(message="Daily standup", trigger_at=trigger_iso, recurrence="DAILY")
    assert rem.id is not None
    assert rem.recurrence == RecurrenceRule.DAILY

    # Complete reminder -> auto-schedules next day
    completed = rem_mgr.complete_reminder(rem.id)
    assert completed.status == ReminderStatus.COMPLETED

    all_rems = rem_mgr.list_reminders()
    assert len(all_rems) == 2
    # Second reminder should be PENDING
    assert all_rems[1].status == ReminderStatus.PENDING
    assert all_rems[1].recurrence == RecurrenceRule.DAILY


def test_notes_crud_and_search():
    """Verify note creation, listing, searching, and deletion."""
    db = ProductivityDatabase(db_path=":memory:")
    note_mgr = NoteManager(db=db)

    n1 = note_mgr.create_note(title="Sensors", content="Buy MEMS microphone and ultrasonic transducer", tags=["hardware", "vibrawave"])
    assert n1.id is not None
    assert "hardware" in n1.tags

    n2 = note_mgr.create_note(title="Meeting notes", content="Discussed Tamil STT accuracy improvements")

    # Search
    results = note_mgr.search_notes("transducer")
    assert len(results) == 1
    assert results[0].title == "Sensors"

    # List
    all_notes = note_mgr.list_notes()
    assert len(all_notes) == 2

    # Delete
    deleted = note_mgr.delete_note(n1.id)
    assert deleted is True
    assert len(note_mgr.list_notes()) == 1


def test_timers_countdown_and_cancellation():
    """Verify in-memory countdown timers."""
    timer_mgr = TimerManager()

    # Create timer
    t = timer_mgr.create_timer(duration_seconds=120.0, label="Tea timer")
    assert t.id is not None
    assert t.status == TimerStatus.RUNNING
    assert 115.0 <= t.remaining_seconds <= 120.0

    # Get active
    active = timer_mgr.get_active_timers()
    assert len(active) >= 1

    # Cancel timer
    cancelled = timer_mgr.cancel_timer(t.id)
    assert cancelled is not None
    assert cancelled.status == TimerStatus.CANCELLED


def test_scheduler_startup_recovery():
    """Verify scheduler handles past-due reminders gracefully on startup."""
    db = ProductivityDatabase(db_path=":memory:")
    rem_mgr = ReminderManager(db=db)
    sched = ProductivityScheduler(db=db, reminder_mgr=rem_mgr)

    # Insert 3 past-due reminders
    past_iso = (datetime.now() - timedelta(minutes=10)).isoformat()
    rem_mgr.create_reminder(message="Past reminder 1", trigger_at=past_iso)
    rem_mgr.create_reminder(message="Past reminder 2", trigger_at=past_iso)
    rem_mgr.create_reminder(message="Past reminder 3", trigger_at=past_iso)

    # Startup recovery
    report = sched.recover_on_startup()
    assert report["recovered_count"] == 3
    assert len(db.get_due_reminders(datetime.now().isoformat())) == 0


def test_productivity_manager_facade():
    """Verify centralized ProductivityManager facade methods."""
    db = ProductivityDatabase(db_path=":memory:")
    tasks = TaskManager(db=db)
    rems = ReminderManager(db=db)
    notes = NoteManager(db=db)
    timers = TimerManager()
    sched = ProductivityScheduler(db=db, reminder_mgr=rems)

    facade = ProductivityManager(db=db, tasks=tasks, reminders=rems, notes=notes, timers=timers, scheduler=sched)

    # Task creation via natural due date
    task = facade.create_task(title="Submit report tomorrow at 5 PM")
    assert task["id"] is not None
    assert task["due_at"] is not None

    # Reminder creation
    rem = facade.create_reminder(message="Check email in 15 minutes")
    assert rem["id"] is not None

    # Note creation
    note = facade.create_note(title="Project Idea", content="Build a voice assistant")
    assert note["id"] is not None

    # Timer creation via text
    timer = facade.create_timer(duration_text="5 minutes", label="Pomodoro")
    assert timer["duration_seconds"] == 300.0


def test_intent_parsing_and_tool_execution():
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

    # Verify tool execution in ToolRegistry
    for t_name in ["create_task", "list_tasks", "complete_task", "create_reminder", "list_reminders", "create_note", "list_notes", "create_timer", "get_timer_status"]:
        entry = tool_registry.get(t_name)
        assert entry is not None, f"Tool {t_name} is not registered"
        schema, handler = entry
        assert schema.permission.value.lower() == "safe"


def run_all():
    """Run all Phase 10 tests sequentially."""
    print("=" * 60)
    print("Running Phase 10 Productivity & Task System Test Suite")
    print("=" * 60)

    tests = [
        ("Task CRUD & Priorities", test_task_crud),
        ("Natural Date/Time Parsing", test_natural_datetime_parsing),
        ("Reminders & Recurrence", test_reminders_and_recurrence),
        ("Notes CRUD & Search", test_notes_crud_and_search),
        ("Timers & Countdown", test_timers_countdown_and_cancellation),
        ("Scheduler & Startup Recovery", test_scheduler_startup_recovery),
        ("Productivity Manager Facade", test_productivity_manager_facade),
        ("Intent Parsing & Tool Execution", test_intent_parsing_and_tool_execution),
    ]

    passed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as exc:
            print(f"  [FAIL] {name}: {exc}")
            raise

    print("=" * 60)
    print(f"All {passed}/{len(tests)} Phase 10 tests passed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    run_all()
