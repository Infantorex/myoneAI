"""Productivity and personal task tool handlers for PC assistant (Phase 10).

Provides tool handlers for Tasks, Reminders, Notes, and Timers with bilingual feedback.
"""

import logging
from typing import Any, Dict, List, Optional

from app.productivity.manager import productivity_manager
from app.tools.schemas import ToolResult

logger = logging.getLogger("myoneAI.tools.productivity")


# ------------------------------------------------------------------------------
# Task Tools
# ------------------------------------------------------------------------------

def create_task(
    title: str,
    description: str = "",
    priority: str = "MEDIUM",
    due_at: Optional[str] = None,
) -> ToolResult:
    """Create a new task."""
    try:
        task = productivity_manager.create_task(
            title=title,
            description=description,
            priority=priority,
            due_at=due_at,
        )
        msg = f"Task created: '{task['title']}' (Priority: {task['priority']}). பணி சேர்க்கப்பட்டது."
        return ToolResult(
            success=True,
            tool="create_task",
            message=msg,
            data=task,
        )
    except Exception as exc:
        logger.error("Failed to create task: %s", exc)
        return ToolResult(
            success=False,
            tool="create_task",
            message=f"Failed to create task: {exc}",
            error=str(exc),
        )


def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 20,
) -> ToolResult:
    """List saved user tasks."""
    try:
        tasks = productivity_manager.list_tasks(status=status, priority=priority, limit=limit)
        if not tasks:
            msg = "You have no saved tasks matching your request. உங்களிடம் பணிகள் எதுவும் இல்லை."
            return ToolResult(
                success=True,
                tool="list_tasks",
                message=msg,
                data={"tasks": []},
            )

        task_strings = []
        for t in tasks:
            status_tag = f"[{t['status']}]"
            priority_tag = f"({t['priority']})"
            due_tag = f" - Due: {t['due_at'][:16]}" if t.get("due_at") else ""
            task_strings.append(f"• #{t['id']} {t['title']} {priority_tag} {status_tag}{due_tag}")

        summary = f"You have {len(tasks)} tasks:\n" + "\n".join(task_strings)
        tamil_summary = f"{len(tasks)} பணிகள் உள்ளன."
        full_msg = f"{summary}\n{tamil_summary}"

        return ToolResult(
            success=True,
            tool="list_tasks",
            message=full_msg,
            data={"tasks": tasks, "count": len(tasks)},
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="list_tasks",
            message=f"Failed to list tasks: {exc}",
            error=str(exc),
        )


def complete_task(
    task_id: Optional[int] = None,
    title: Optional[str] = None,
) -> ToolResult:
    """Mark a task as completed."""
    try:
        task = productivity_manager.complete_task(task_id=task_id, title=title)
        if not task:
            return ToolResult(
                success=False,
                tool="complete_task",
                message="No matching task found to mark as completed. பணி கிடைக்கவில்லை.",
            )

        msg = f"Task completed: '{task['title']}'. பணி வெற்றிகரமாக முடிக்கப்பட்டது."
        return ToolResult(
            success=True,
            tool="complete_task",
            message=msg,
            data=task,
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="complete_task",
            message=f"Failed to complete task: {exc}",
            error=str(exc),
        )


def delete_task(
    task_id: Optional[int] = None,
    title: Optional[str] = None,
) -> ToolResult:
    """Delete a task (requires confirmation)."""
    try:
        deleted = productivity_manager.delete_task(task_id=task_id, title=title)
        if not deleted:
            return ToolResult(
                success=False,
                tool="delete_task",
                message="Task not found to delete. பணி கிடைக்கவில்லை.",
            )

        msg = f"Task '{title or task_id}' deleted. பணி நீக்கப்பட்டது."
        return ToolResult(
            success=True,
            tool="delete_task",
            message=msg,
            data={"deleted": True, "task_id": task_id, "title": title},
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="delete_task",
            message=f"Failed to delete task: {exc}",
            error=str(exc),
        )


def clear_all_tasks() -> ToolResult:
    """Clear all tasks (requires confirmation)."""
    try:
        count = productivity_manager.clear_all_tasks()
        msg = f"Cleared all {count} tasks. அனைத்து பணிகளும் நீக்கப்பட்டன."
        return ToolResult(
            success=True,
            tool="clear_all_tasks",
            message=msg,
            data={"deleted_count": count},
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="clear_all_tasks",
            message=f"Failed to clear tasks: {exc}",
            error=str(exc),
        )


# ------------------------------------------------------------------------------
# Reminder Tools
# ------------------------------------------------------------------------------

def create_reminder(
    message: str,
    trigger_at: Optional[str] = None,
    recurrence: str = "NONE",
) -> ToolResult:
    """Schedule a new reminder."""
    try:
        rem = productivity_manager.create_reminder(
            message=message,
            trigger_at=trigger_at,
            recurrence=recurrence,
        )
        time_str = rem["trigger_at"][:16].replace("T", " ")
        rec_tag = f" ({rem['recurrence']})" if rem['recurrence'] != "NONE" else ""
        msg = f"Reminder set for {time_str}{rec_tag}: '{rem['message']}'. நினைவூட்டல் அமைக்கப்பட்டது."
        return ToolResult(
            success=True,
            tool="create_reminder",
            message=msg,
            data=rem,
        )
    except Exception as exc:
        logger.error("Failed to create reminder: %s", exc)
        return ToolResult(
            success=False,
            tool="create_reminder",
            message=f"Failed to create reminder: {exc}",
            error=str(exc),
        )


def list_reminders(
    status: Optional[str] = None,
    limit: int = 20,
) -> ToolResult:
    """List scheduled reminders."""
    try:
        rems = productivity_manager.list_reminders(status=status, limit=limit)
        if not rems:
            msg = "You have no scheduled reminders. உங்களுக்கு நினைவூட்டல்கள் எதுவும் இல்லை."
            return ToolResult(
                success=True,
                tool="list_reminders",
                message=msg,
                data={"reminders": []},
            )

        rem_strings = []
        for r in rems:
            time_str = r['trigger_at'][:16].replace("T", " ")
            rec_tag = f" [{r['recurrence']}]" if r['recurrence'] != "NONE" else ""
            rem_strings.append(f"• #{r['id']} {time_str}{rec_tag}: {r['message']} ({r['status']})")

        summary = f"You have {len(rems)} reminders:\n" + "\n".join(rem_strings)
        tamil_summary = f"{len(rems)} நினைவூட்டல்கள் உள்ளன."
        full_msg = f"{summary}\n{tamil_summary}"

        return ToolResult(
            success=True,
            tool="list_reminders",
            message=full_msg,
            data={"reminders": rems, "count": len(rems)},
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="list_reminders",
            message=f"Failed to list reminders: {exc}",
            error=str(exc),
        )


def cancel_reminder(
    reminder_id: Optional[int] = None,
    message: Optional[str] = None,
) -> ToolResult:
    """Cancel a scheduled reminder (requires confirmation)."""
    try:
        rem = productivity_manager.cancel_reminder(reminder_id=reminder_id, message=message)
        if not rem:
            return ToolResult(
                success=False,
                tool="cancel_reminder",
                message="Reminder not found to cancel. நினைவூட்டல் கிடைக்கவில்லை.",
            )

        msg = f"Cancelled reminder: '{rem['message']}'. நினைவூட்டல் ரத்து செய்யப்பட்டது."
        return ToolResult(
            success=True,
            tool="cancel_reminder",
            message=msg,
            data=rem,
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="cancel_reminder",
            message=f"Failed to cancel reminder: {exc}",
            error=str(exc),
        )


def clear_all_reminders() -> ToolResult:
    """Clear all reminders (requires confirmation)."""
    try:
        count = productivity_manager.clear_all_reminders()
        msg = f"Cleared all {count} reminders. அனைத்து நினைவூட்டல்களும் நீக்கப்பட்டன."
        return ToolResult(
            success=True,
            tool="clear_all_reminders",
            message=msg,
            data={"deleted_count": count},
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="clear_all_reminders",
            message=f"Failed to clear reminders: {exc}",
            error=str(exc),
        )


# ------------------------------------------------------------------------------
# Note Tools
# ------------------------------------------------------------------------------

def create_note(
    title: str = "",
    content: str = "",
    tags: Optional[List[str]] = None,
) -> ToolResult:
    """Create a user note."""
    try:
        note = productivity_manager.create_note(title=title, content=content, tags=tags)
        msg = f"Note saved: '{note['title']}'. குறிப்பு சேமிக்கப்பட்டது."
        return ToolResult(
            success=True,
            tool="create_note",
            message=msg,
            data=note,
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="create_note",
            message=f"Failed to save note: {exc}",
            error=str(exc),
        )


def list_notes(limit: int = 20) -> ToolResult:
    """List recently saved notes."""
    try:
        notes = productivity_manager.list_notes(limit=limit)
        if not notes:
            return ToolResult(
                success=True,
                tool="list_notes",
                message="You have no saved notes. குறிப்புகள் எதுவும் இல்லை.",
                data={"notes": []},
            )

        note_strings = [f"• #{n['id']} {n['title']}: {n['content'][:50]}..." for n in notes]
        summary = f"You have {len(notes)} notes:\n" + "\n".join(note_strings)
        tamil_summary = f"{len(notes)} குறிப்புகள் உள்ளன."

        return ToolResult(
            success=True,
            tool="list_notes",
            message=f"{summary}\n{tamil_summary}",
            data={"notes": notes, "count": len(notes)},
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="list_notes",
            message=f"Failed to list notes: {exc}",
            error=str(exc),
        )


def search_notes(query: str, limit: int = 10) -> ToolResult:
    """Search notes by keyword."""
    try:
        notes = productivity_manager.search_notes(query=query, limit=limit)
        if not notes:
            return ToolResult(
                success=True,
                tool="search_notes",
                message=f"No notes found matching '{query}'. குறிப்புகள் கிடைக்கவில்லை.",
                data={"notes": []},
            )

        note_strings = [f"• #{n['id']} {n['title']}: {n['content']}" for n in notes]
        summary = f"Found {len(notes)} notes matching '{query}':\n" + "\n".join(note_strings)

        return ToolResult(
            success=True,
            tool="search_notes",
            message=summary,
            data={"notes": notes, "count": len(notes)},
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="search_notes",
            message=f"Failed to search notes: {exc}",
            error=str(exc),
        )


def delete_note(
    note_id: Optional[int] = None,
    title: Optional[str] = None,
) -> ToolResult:
    """Delete a note (requires confirmation)."""
    try:
        deleted = productivity_manager.delete_note(note_id=note_id, title=title)
        if not deleted:
            return ToolResult(
                success=False,
                tool="delete_note",
                message="Note not found to delete. குறிப்பு கிடைக்கவில்லை.",
            )

        msg = f"Note '{title or note_id}' deleted. குறிப்பு நீக்கப்பட்டது."
        return ToolResult(
            success=True,
            tool="delete_note",
            message=msg,
            data={"deleted": True, "note_id": note_id, "title": title},
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="delete_note",
            message=f"Failed to delete note: {exc}",
            error=str(exc),
        )


def clear_all_notes() -> ToolResult:
    """Clear all notes (requires confirmation)."""
    try:
        count = productivity_manager.clear_all_notes()
        msg = f"Cleared all {count} notes. அனைத்து குறிப்புகளும் நீக்கப்பட்டன."
        return ToolResult(
            success=True,
            tool="clear_all_notes",
            message=msg,
            data={"deleted_count": count},
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="clear_all_notes",
            message=f"Failed to clear notes: {exc}",
            error=str(exc),
        )


# ------------------------------------------------------------------------------
# Timer Tools
# ------------------------------------------------------------------------------

def create_timer(
    duration_seconds: Optional[float] = None,
    duration_text: Optional[str] = None,
    label: str = "Timer",
) -> ToolResult:
    """Set an in-memory countdown timer."""
    try:
        timer = productivity_manager.create_timer(
            duration_seconds=duration_seconds,
            duration_text=duration_text,
            label=label,
        )
        mins = timer["duration_seconds"] / 60
        if mins >= 1:
            dur_str = f"{mins:.0f} minute{'s' if mins != 1 else ''}"
            tamil_dur = f"{mins:.0f} நிமிடங்கள்"
        else:
            dur_str = f"{timer['duration_seconds']:.0f} seconds"
            tamil_dur = f"{timer['duration_seconds']:.0f} வினாடிகள்"

        msg = f"Timer set for {dur_str} ('{timer['label']}'). {tamil_dur} டைமர் வைக்கப்பட்டது."
        return ToolResult(
            success=True,
            tool="create_timer",
            message=msg,
            data=timer,
        )
    except Exception as exc:
        logger.error("Failed to create timer: %s", exc)
        return ToolResult(
            success=False,
            tool="create_timer",
            message=f"Failed to set timer: {exc}",
            error=str(exc),
        )


def cancel_timer(timer_id: Optional[str] = None) -> ToolResult:
    """Cancel an active timer."""
    try:
        timer = productivity_manager.cancel_timer(timer_id=timer_id)
        if not timer:
            return ToolResult(
                success=False,
                tool="cancel_timer",
                message="No active timer found to cancel. செயலில் உள்ள டைமர் எதுவும் இல்லை.",
            )

        msg = f"Timer '{timer['label']}' cancelled. டைமர் ரத்து செய்யப்பட்டது."
        return ToolResult(
            success=True,
            tool="cancel_timer",
            message=msg,
            data=timer,
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="cancel_timer",
            message=f"Failed to cancel timer: {exc}",
            error=str(exc),
        )


def get_timer_status(timer_id: Optional[str] = None) -> ToolResult:
    """Check remaining time on active timer."""
    try:
        timer = productivity_manager.get_timer_status(timer_id=timer_id)
        if not timer or timer["status"] != "RUNNING":
            return ToolResult(
                success=True,
                tool="get_timer_status",
                message="No active timers currently running. செயலில் உள்ள டைமர்கள் எதுவும் இல்லை.",
                data={"active": False},
            )

        rem = timer["remaining_seconds"]
        mins = int(rem // 60)
        secs = int(rem % 60)
        time_left_str = f"{mins}m {secs}s" if mins > 0 else f"{secs} seconds"
        tamil_left = f"{mins} நிமிடம் {secs} வினாடி" if mins > 0 else f"{secs} வினாடிகள்"

        msg = f"Timer '{timer['label']}' has {time_left_str} remaining. மீதமுள்ள நேரம்: {tamil_left}."
        return ToolResult(
            success=True,
            tool="get_timer_status",
            message=msg,
            data=timer,
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="get_timer_status",
            message=f"Failed to read timer status: {exc}",
            error=str(exc),
        )
