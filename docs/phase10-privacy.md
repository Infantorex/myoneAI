# Phase 10: Productivity & Personal Task System Privacy Architecture

## Overview
**myoneAI — Tamil JARVIS** provides a 100% local, SQLite-backed personal task, reminder, note, and timer subsystem. Built with strict privacy-first constraints for personal computing, user tasks and personal notes remain entirely confidential on the user's laptop.

---

## 1. Data Storage & Local Persistence

- **Local SQLite Database**: All tasks, scheduled reminders, and notebook entries are stored exclusively in the local database:
  ```text
  data/productivity.db
  ```
- **Git Version Control Exclusion**: `data/productivity.db`, `data/*.sqlite`, and `data/*.sqlite3` are strictly ignored by `.gitignore`. Personal tasks, meeting notes, and reminders are **never** committed or tracked in version control.
- **In-Memory Timers**: Active countdown timers run solely in-memory (`app/productivity/timers.py`) and leave zero persistent trace on disk after completion.

---

## 2. AI Transmission Policy & Minimization

- **No Bulk Database Uploads**: The productivity database is **never** uploaded or dumped in bulk to any third-party or cloud AI provider.
- **On-Demand Query Minimization**: When a user asks a productivity question (e.g. *"What are my tasks today?"*, *"Search my notes for Arduino"*), only the matching retrieved items (maximum 5–10 items) are formatted as structured text and sent in the immediate conversational turn context.
- **No Background Data Leaks**: The periodic background reminder scheduler evaluates due times locally without transmitting timestamps or reminder text to cloud services.

---

## 3. Data Retention & User Control

Users have complete autonomy to inspect, modify, and permanently remove their productivity data:

- **Individual Deletions**:
  - `delete_task(task_id/title)`
  - `delete_note(note_id/title)`
  - `cancel_reminder(reminder_id/message)`
- **Bulk Data Wiping (Requires Confirmation)**:
  - *"Delete all my tasks"* (`clear_all_tasks`)
  - *"Delete all my notes"* (`clear_all_notes`)
  - *"Clear all reminders"* (`clear_all_reminders`)
- **Direct File Removal**: Deleting `data/productivity.db` from disk completely wipes all task and reminder history.

---

## 4. Disabling Productivity Features

Productivity features can be completely disabled in configuration:

In `.env`:
```env
PRODUCTIVITY_ENABLED=false
```

When set to `false`, the background reminder scheduler will not start, no database queries execute automatically, and productivity tools will remain inactive.
