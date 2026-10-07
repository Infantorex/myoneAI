"""SQLite database storage engine for Tasks, Reminders, and Notes (Phase 10)."""

import json
import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import Settings, get_settings
from app.productivity.models import (
    NoteItem,
    RecurrenceRule,
    ReminderItem,
    ReminderStatus,
    TaskItem,
    TaskPriority,
    TaskStatus,
)

logger = logging.getLogger("myoneAI.productivity.database")


def _now_iso() -> str:
    """Return current timestamp in ISO 8601 format."""
    return datetime.now().isoformat()


class ProductivityDatabase:
    """Thread-safe SQLite persistent store for productivity records."""

    def __init__(self, db_path: Optional[str] = None, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        if db_path:
            self.db_path = db_path
        else:
            configured_path = getattr(self.settings, "productivity_database_path", "data/productivity.db")
            p = Path(configured_path)
            if not p.is_absolute():
                p = self.settings.base_dir / p
            self.db_path = str(p)

        self._lock = threading.Lock()
        self._mem_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._mem_conn.row_factory = sqlite3.Row
            self._mem_conn.execute("PRAGMA foreign_keys = ON")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a connection with row factory, foreign keys, and performance pragmas."""
        if self.db_path == ":memory:" and self._mem_conn is not None:
            return self._mem_conn
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA cache_size = -2000;")
        conn.execute("PRAGMA temp_store = MEMORY;")
        return conn

    def _close_connection(self, conn: sqlite3.Connection) -> None:
        """Close connection unless it is the persistent in-memory test connection."""
        if conn is not self._mem_conn:
            conn.close()

    def _init_db(self) -> None:
        """Initialize database tables and indexes."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                # 1. Tasks Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT DEFAULT '',
                        priority TEXT DEFAULT 'MEDIUM',
                        status TEXT DEFAULT 'TODO',
                        due_at TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due_at ON tasks(due_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status_due ON tasks(status, due_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_updated ON tasks(updated_at DESC)")

                # 2. Reminders Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reminders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message TEXT NOT NULL,
                        trigger_at TEXT NOT NULL,
                        status TEXT DEFAULT 'PENDING',
                        recurrence TEXT DEFAULT 'NONE',
                        created_at TEXT NOT NULL,
                        completed_at TEXT
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminders_trigger_at ON reminders(trigger_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminders_status_trigger ON reminders(status, trigger_at)")

                # 3. Notes Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        tags TEXT DEFAULT '[]',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at DESC)")
                conn.commit()
            except Exception as exc:
                logger.error("Failed to initialize productivity database: %s", exc)
                raise
            finally:
                self._close_connection(conn)

    # --------------------------------------------------------------------------
    # Task Operations
    # --------------------------------------------------------------------------

    def add_task(self, task: TaskItem) -> TaskItem:
        """Insert a new task into the database."""
        now = _now_iso()
        created_at = task.created_at or now
        updated_at = task.updated_at or now
        priority_val = task.priority.value if isinstance(task.priority, TaskPriority) else str(task.priority)
        status_val = task.status.value if isinstance(task.status, TaskStatus) else str(task.status)

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO tasks (title, description, priority, status, due_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (task.title.strip(), task.description.strip(), priority_val, status_val, task.due_at, created_at, updated_at),
                )
                conn.commit()
                task.id = cursor.lastrowid
                task.created_at = created_at
                task.updated_at = updated_at
                return task
            finally:
                self._close_connection(conn)

    def get_task(self, task_id: int) -> Optional[TaskItem]:
        """Fetch a specific task by its numeric ID."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return self._row_to_task(row)
            finally:
                self._close_connection(conn)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        limit: int = 20,
    ) -> List[TaskItem]:
        """List tasks with optional status and priority filtering."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                query = "SELECT * FROM tasks WHERE 1=1"
                params: List[Any] = []

                if status is not None:
                    query += " AND status = ?"
                    params.append(status.value if isinstance(status, TaskStatus) else str(status))
                if priority is not None:
                    query += " AND priority = ?"
                    params.append(priority.value if isinstance(priority, TaskPriority) else str(priority))

                query += " ORDER BY CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 WHEN 'LOW' THEN 3 ELSE 4 END, id DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                return [self._row_to_task(row) for row in cursor.fetchall()]
            finally:
                self._close_connection(conn)

    def search_tasks(self, query_text: str, limit: int = 10) -> List[TaskItem]:
        """Search tasks by title or description keyword match."""
        pattern = f"%{query_text.strip()}%"
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM tasks
                    WHERE title LIKE ? OR description LIKE ?
                    ORDER BY id DESC LIMIT ?
                    """,
                    (pattern, pattern, limit),
                )
                return [self._row_to_task(row) for row in cursor.fetchall()]
            finally:
                self._close_connection(conn)

    def update_task(
        self,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        status: Optional[TaskStatus] = None,
        due_at: Optional[str] = None,
    ) -> Optional[TaskItem]:
        """Update existing task fields."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
                row = cursor.fetchone()
                if not row:
                    return None

                updates: List[str] = []
                params: List[Any] = []

                if title is not None:
                    updates.append("title = ?")
                    params.append(title.strip())
                if description is not None:
                    updates.append("description = ?")
                    params.append(description.strip())
                if priority is not None:
                    updates.append("priority = ?")
                    params.append(priority.value if isinstance(priority, TaskPriority) else str(priority))
                if status is not None:
                    updates.append("status = ?")
                    params.append(status.value if isinstance(status, TaskStatus) else str(status))
                if due_at is not None:
                    updates.append("due_at = ?")
                    params.append(due_at)

                updates.append("updated_at = ?")
                params.append(_now_iso())
                params.append(task_id)

                sql = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(sql, params)
                conn.commit()

                cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
                return self._row_to_task(cursor.fetchone())
            finally:
                self._close_connection(conn)

    def complete_task(self, task_id: int) -> Optional[TaskItem]:
        """Mark task as COMPLETED."""
        return self.update_task(task_id, status=TaskStatus.COMPLETED)

    def delete_task(self, task_id: int) -> bool:
        """Delete a single task by ID."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                conn.commit()
                return cursor.rowcount > 0
            finally:
                self._close_connection(conn)

    def clear_all_tasks(self) -> int:
        """Permanently delete all tasks."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM tasks")
                conn.commit()
                return cursor.rowcount
            finally:
                self._close_connection(conn)

    def _row_to_task(self, row: sqlite3.Row) -> TaskItem:
        """Helper converting SQL row to TaskItem model."""
        return TaskItem(
            id=row["id"],
            title=row["title"],
            description=row["description"] or "",
            priority=TaskPriority(row["priority"]) if row["priority"] in TaskPriority._value2member_map_ else TaskPriority.MEDIUM,
            status=TaskStatus(row["status"]) if row["status"] in TaskStatus._value2member_map_ else TaskStatus.TODO,
            due_at=row["due_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # --------------------------------------------------------------------------
    # Reminder Operations
    # --------------------------------------------------------------------------

    def add_reminder(self, reminder: ReminderItem) -> ReminderItem:
        """Insert a new reminder."""
        now = _now_iso()
        created_at = reminder.created_at or now
        status_val = reminder.status.value if isinstance(reminder.status, ReminderStatus) else str(reminder.status)
        rec_val = reminder.recurrence.value if isinstance(reminder.recurrence, RecurrenceRule) else str(reminder.recurrence)

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO reminders (message, trigger_at, status, recurrence, created_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (reminder.message.strip(), reminder.trigger_at, status_val, rec_val, created_at, reminder.completed_at),
                )
                conn.commit()
                reminder.id = cursor.lastrowid
                reminder.created_at = created_at
                return reminder
            finally:
                self._close_connection(conn)

    def get_reminder(self, reminder_id: int) -> Optional[ReminderItem]:
        """Fetch reminder by ID."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return self._row_to_reminder(row)
            finally:
                self._close_connection(conn)

    def list_reminders(
        self,
        status: Optional[ReminderStatus] = None,
        limit: int = 20,
    ) -> List[ReminderItem]:
        """List reminders ordered chronologically by trigger time."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                if status is not None:
                    val = status.value if isinstance(status, ReminderStatus) else str(status)
                    cursor.execute(
                        "SELECT * FROM reminders WHERE status = ? ORDER BY trigger_at ASC LIMIT ?",
                        (val, limit),
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM reminders ORDER BY trigger_at ASC LIMIT ?",
                        (limit,),
                    )
                return [self._row_to_reminder(row) for row in cursor.fetchall()]
            finally:
                self._close_connection(conn)

    def get_due_reminders(self, current_iso: str) -> List[ReminderItem]:
        """Fetch pending reminders whose trigger time is less than or equal to current_iso."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM reminders
                    WHERE status = 'PENDING' AND trigger_at <= ?
                    ORDER BY trigger_at ASC
                    """,
                    (current_iso,),
                )
                return [self._row_to_reminder(row) for row in cursor.fetchall()]
            finally:
                self._close_connection(conn)

    def update_reminder_status(
        self,
        reminder_id: int,
        status: ReminderStatus,
        completed_at: Optional[str] = None,
    ) -> Optional[ReminderItem]:
        """Update reminder status."""
        val = status.value if isinstance(status, ReminderStatus) else str(status)
        now = completed_at or (_now_iso() if status in (ReminderStatus.TRIGGERED, ReminderStatus.COMPLETED) else None)

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE reminders SET status = ?, completed_at = ? WHERE id = ?",
                    (val, now, reminder_id),
                )
                conn.commit()
                cursor.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,))
                row = cursor.fetchone()
                return self._row_to_reminder(row) if row else None
            finally:
                self._close_connection(conn)

    def delete_reminder(self, reminder_id: int) -> bool:
        """Delete reminder by ID."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
                conn.commit()
                return cursor.rowcount > 0
            finally:
                self._close_connection(conn)

    def clear_all_reminders(self) -> int:
        """Clear all reminders."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM reminders")
                conn.commit()
                return cursor.rowcount
            finally:
                self._close_connection(conn)

    def _row_to_reminder(self, row: sqlite3.Row) -> ReminderItem:
        return ReminderItem(
            id=row["id"],
            message=row["message"],
            trigger_at=row["trigger_at"],
            status=ReminderStatus(row["status"]) if row["status"] in ReminderStatus._value2member_map_ else ReminderStatus.PENDING,
            recurrence=RecurrenceRule(row["recurrence"]) if row["recurrence"] in RecurrenceRule._value2member_map_ else RecurrenceRule.NONE,
            created_at=row["created_at"],
            completed_at=row["completed_at"],
        )

    # --------------------------------------------------------------------------
    # Notes Operations
    # --------------------------------------------------------------------------

    def add_note(self, note: NoteItem) -> NoteItem:
        """Insert a new note."""
        now = _now_iso()
        created_at = note.created_at or now
        updated_at = note.updated_at or now
        tags_json = json.dumps(note.tags)

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO notes (title, content, tags, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (note.title.strip(), note.content.strip(), tags_json, created_at, updated_at),
                )
                conn.commit()
                note.id = cursor.lastrowid
                note.created_at = created_at
                note.updated_at = updated_at
                return note
            finally:
                self._close_connection(conn)

    def get_note(self, note_id: int) -> Optional[NoteItem]:
        """Fetch note by ID."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return self._row_to_note(row)
            finally:
                self._close_connection(conn)

    def list_notes(self, limit: int = 20) -> List[NoteItem]:
        """List notes ordered by most recently updated."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM notes ORDER BY updated_at DESC, id DESC LIMIT ?", (limit,))
                return [self._row_to_note(row) for row in cursor.fetchall()]
            finally:
                self._close_connection(conn)

    def search_notes(self, query_text: str, limit: int = 10) -> List[NoteItem]:
        """Search notes by title, content, or tags keyword."""
        pattern = f"%{query_text.strip()}%"
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM notes
                    WHERE title LIKE ? OR content LIKE ? OR tags LIKE ?
                    ORDER BY updated_at DESC LIMIT ?
                    """,
                    (pattern, pattern, pattern, limit),
                )
                return [self._row_to_note(row) for row in cursor.fetchall()]
            finally:
                self._close_connection(conn)

    def update_note(
        self,
        note_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[NoteItem]:
        """Update note title, content, or tags."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
                row = cursor.fetchone()
                if not row:
                    return None

                updates: List[str] = []
                params: List[Any] = []

                if title is not None:
                    updates.append("title = ?")
                    params.append(title.strip())
                if content is not None:
                    updates.append("content = ?")
                    params.append(content.strip())
                if tags is not None:
                    updates.append("tags = ?")
                    params.append(json.dumps(tags))

                updates.append("updated_at = ?")
                params.append(_now_iso())
                params.append(note_id)

                sql = f"UPDATE notes SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(sql, params)
                conn.commit()

                cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
                return self._row_to_note(cursor.fetchone())
            finally:
                self._close_connection(conn)

    def delete_note(self, note_id: int) -> bool:
        """Delete note by ID."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
                conn.commit()
                return cursor.rowcount > 0
            finally:
                self._close_connection(conn)

    def clear_all_notes(self) -> int:
        """Clear all notes."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM notes")
                conn.commit()
                return cursor.rowcount
            finally:
                self._close_connection(conn)

    def _row_to_note(self, row: sqlite3.Row) -> NoteItem:
        tags_raw = row["tags"]
        try:
            tags_list = json.loads(tags_raw) if tags_raw else []
        except Exception:
            tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

        return NoteItem(
            id=row["id"],
            title=row["title"],
            content=row["content"],
            tags=tags_list,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


# Global Database singleton
productivity_db = ProductivityDatabase()
