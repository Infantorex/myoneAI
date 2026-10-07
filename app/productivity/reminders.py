"""Scheduled reminders and natural date/time parsing engine (Phase 10)."""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import Settings, get_settings
from app.productivity.database import ProductivityDatabase, productivity_db
from app.productivity.models import RecurrenceRule, ReminderItem, ReminderStatus

logger = logging.getLogger("myoneAI.productivity.reminders")


def parse_natural_datetime(
    text: str,
    base_time: Optional[datetime] = None,
) -> Tuple[Optional[datetime], RecurrenceRule, str]:
    """Parse relative and natural date/time expressions in English, Tamil, and Tanglish.

    Args:
        text: Natural language text containing time expressions and reminder message.
        base_time: Reference base datetime (defaults to datetime.now()).

    Returns:
        Tuple of (target_datetime, recurrence_rule, cleaned_message).
    """
    if not text or not text.strip():
        return None, RecurrenceRule.NONE, ""

    now = base_time or datetime.now()
    raw = text.strip()
    clean = raw
    recurrence = RecurrenceRule.NONE
    target_dt: Optional[datetime] = None

    # 1. Recurrence Detection ("every day at 8 AM", "daily at 9 AM", "every Monday at 10 AM")
    daily_match = re.search(r"(?i)\b(?:every\s+day|daily|தினமும்|ஒவ்வொரு\s+நாளும்)\b", raw)
    weekly_match = re.search(r"(?i)\b(?:every\s+week|weekly|ஒவ்வொரு\s+வாரமும்|every\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b", raw)

    if daily_match:
        recurrence = RecurrenceRule.DAILY
        clean = re.sub(r"(?i)\b(?:every\s+day|daily|தினமும்|ஒவ்வொரு\s+நாளும்)\b", "", clean)
    elif weekly_match:
        recurrence = RecurrenceRule.WEEKLY
        clean = re.sub(r"(?i)\b(?:every\s+week|weekly|ஒவ்வொரு\s+வாரமும்)\b", "", clean)

    # 2. Relative offset ("in 10 minutes", "in 30 mins", "after 1 hour", "in 2 hours", "10 minutes-ல்", "30 நிமிடத்தில்")
    rel_match = re.search(
        r"(?i)\b(?:in|after)\s+(\d+)\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours|s|sec|secs|second|seconds)\b",
        raw,
    )
    tamil_rel_match = re.search(
        r"(?i)(\d+)\s*(?:நிமிடம்|நிமிடத்தில்|மணி|மணியில்|minutes?-ல்|hours?-ல்)",
        raw,
    )

    if rel_match:
        val = int(rel_match.group(1))
        unit = rel_match.group(2).lower()
        if unit.startswith("m"):
            target_dt = now + timedelta(minutes=val)
        elif unit.startswith("h"):
            target_dt = now + timedelta(hours=val)
        elif unit.startswith("s"):
            target_dt = now + timedelta(seconds=val)
        clean = clean.replace(rel_match.group(0), "")
    elif tamil_rel_match:
        val = int(tamil_rel_match.group(1))
        matched_str = tamil_rel_match.group(0)
        if "மணி" in matched_str or "hour" in matched_str:
            target_dt = now + timedelta(hours=val)
        else:
            target_dt = now + timedelta(minutes=val)
        clean = clean.replace(matched_str, "")

    # 3. Explicit Time ("at 6 PM", "at 9:30 AM", "at 18:00", "மாலை 6 மணிக்கு", "காலை 9 மணிக்கு")
    time_match = re.search(
        r"(?i)\b(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b",
        raw,
    )
    tamil_time_match = re.search(
        r"(?i)(?:காலை|மாலை|இரவு)?\s*(\d{1,2})(?::(\d{2}))?\s*மணிக்கு",
        raw,
    )

    if not target_dt and time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        meridiem = time_match.group(3).lower()

        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0

        # Day target: today vs tomorrow
        day_offset = 0
        if re.search(r"(?i)\b(?:tomorrow|நாளை|நாளைக்கு)\b", raw):
            day_offset = 1
            clean = re.sub(r"(?i)\b(?:tomorrow|நாளை|நாளைக்கு)\b", "", clean)
        elif re.search(r"(?i)\b(?:today|இன்று|இன்னைக்கு)\b", raw):
            day_offset = 0
            clean = re.sub(r"(?i)\b(?:today|இன்று|இன்னைக்கு)\b", "", clean)
        else:
            # If specified time already passed today, assume tomorrow
            candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate <= now and recurrence == RecurrenceRule.NONE:
                day_offset = 1

        target_day = (now + timedelta(days=day_offset)).date()
        target_dt = datetime.combine(target_day, datetime.min.time()).replace(hour=hour, minute=minute, second=0, microsecond=0)
        clean = clean.replace(time_match.group(0), "")

    elif not target_dt and tamil_time_match:
        hour = int(tamil_time_match.group(1))
        minute = int(tamil_time_match.group(2)) if tamil_time_match.group(2) else 0
        is_evening = bool(re.search(r"மாலை|இரவு", raw))
        if is_evening and hour < 12:
            hour += 12

        day_offset = 1 if re.search(r"நாளை|நாளைக்கு", raw) else 0
        clean = re.sub(r"நாளை|நாளைக்கு|இன்று|இன்னைக்கு", "", clean)
        target_day = (now + timedelta(days=day_offset)).date()
        target_dt = datetime.combine(target_day, datetime.min.time()).replace(hour=hour, minute=minute, second=0, microsecond=0)
        clean = clean.replace(tamil_time_match.group(0), "")

    # 4. Period shortcuts ("tonight" -> 20:00, "this evening" -> 18:00, "tomorrow morning" -> 09:00)
    if not target_dt:
        if re.search(r"(?i)\b(?:tonight|இன்று\s+இரவு)\b", raw):
            target_dt = now.replace(hour=20, minute=0, second=0, microsecond=0)
            if target_dt <= now:
                target_dt += timedelta(days=1)
            clean = re.sub(r"(?i)\b(?:tonight|இன்று\s+இரவு)\b", "", clean)
        elif re.search(r"(?i)\b(?:this\s+evening|இன்று\s+மாலை)\b", raw):
            target_dt = now.replace(hour=18, minute=0, second=0, microsecond=0)
            if target_dt <= now:
                target_dt += timedelta(days=1)
            clean = re.sub(r"(?i)\b(?:this\s+evening|இன்று\s+மாலை)\b", "", clean)
        elif re.search(r"(?i)\b(?:tomorrow\s+morning|நாளை\s+காலை)\b", raw):
            target_dt = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            clean = re.sub(r"(?i)\b(?:tomorrow\s+morning|நாளை\s+காலை)\b", "", clean)
        elif re.search(r"(?i)\b(?:tomorrow|நாளை|நாளைக்கு)\b", raw):
            target_dt = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            clean = re.sub(r"(?i)\b(?:tomorrow|நாளை|நாளைக்கு)\b", "", clean)

    # Clean leftover keywords from reminder message
    clean = re.sub(r"(?i)\b(?:remind\s+me\s+(?:to\s+|about\s+)?|set\s+a\s+reminder\s+(?:to\s+|for\s+)?|reminder\s+for|reminder\s+వై|reminder\s+வை|நினைவூட்டு)\b", "", clean)
    clean = re.sub(r"(?i)\b(?:at|on|for|in|about)\b", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    return target_dt, recurrence, clean


class ReminderManager:
    """Business logic for reminder scheduling, recurrence, and lifecycle."""

    def __init__(self, db: Optional[ProductivityDatabase] = None) -> None:
        self.db = db or productivity_db

    def create_reminder(
        self,
        message: str,
        trigger_at: str,
        recurrence: str = "NONE",
    ) -> ReminderItem:
        """Schedule and store a new reminder."""
        if not message or not message.strip():
            raise ValueError("Reminder message cannot be empty.")

        try:
            r_enum = RecurrenceRule(recurrence.upper())
        except Exception:
            r_enum = RecurrenceRule.NONE

        item = ReminderItem(
            message=message.strip(),
            trigger_at=trigger_at,
            status=ReminderStatus.PENDING,
            recurrence=r_enum,
        )
        saved = self.db.add_reminder(item)
        logger.info("Scheduled Reminder #%s: '%s' at %s (Recurrence: %s)", saved.id, saved.message, saved.trigger_at, saved.recurrence.value)
        return saved

    def list_reminders(
        self,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> List[ReminderItem]:
        """List scheduled reminders."""
        s_enum = None
        if status:
            try:
                s_enum = ReminderStatus(status.upper())
            except Exception:
                pass
        return self.db.list_reminders(status=s_enum, limit=limit)

    def get_reminder(self, reminder_id: int) -> Optional[ReminderItem]:
        """Retrieve reminder by ID."""
        return self.db.get_reminder(reminder_id)

    def cancel_reminder(self, reminder_id: int) -> Optional[ReminderItem]:
        """Cancel a pending reminder."""
        return self.db.update_reminder_status(reminder_id, status=ReminderStatus.CANCELLED)

    def cancel_reminder_by_message(self, message_query: str) -> Optional[ReminderItem]:
        """Find pending reminder matching text and cancel it."""
        all_pending = self.list_reminders(status="PENDING", limit=50)
        query_lower = message_query.lower().strip()
        for rem in all_pending:
            if query_lower in rem.message.lower():
                return self.cancel_reminder(rem.id)
        return None

    def complete_reminder(self, reminder_id: int) -> Optional[ReminderItem]:
        """Mark reminder as COMPLETED and schedule next occurrence if recurring."""
        rem = self.db.get_reminder(reminder_id)
        if not rem:
            return None

        updated = self.db.update_reminder_status(reminder_id, status=ReminderStatus.COMPLETED)

        # If recurring, automatically schedule the next occurrence
        if rem.recurrence == RecurrenceRule.DAILY:
            try:
                cur_dt = datetime.fromisoformat(rem.trigger_at)
                next_dt = cur_dt + timedelta(days=1)
                self.create_reminder(message=rem.message, trigger_at=next_dt.isoformat(), recurrence="DAILY")
                logger.info("Rescheduled DAILY reminder '%s' for %s", rem.message, next_dt.isoformat())
            except Exception as exc:
                logger.error("Failed to advance daily reminder: %s", exc)
        elif rem.recurrence == RecurrenceRule.WEEKLY:
            try:
                cur_dt = datetime.fromisoformat(rem.trigger_at)
                next_dt = cur_dt + timedelta(days=7)
                self.create_reminder(message=rem.message, trigger_at=next_dt.isoformat(), recurrence="WEEKLY")
                logger.info("Rescheduled WEEKLY reminder '%s' for %s", rem.message, next_dt.isoformat())
            except Exception as exc:
                logger.error("Failed to advance weekly reminder: %s", exc)

        return updated

    def delete_reminder(self, reminder_id: int) -> bool:
        """Delete reminder by ID."""
        return self.db.delete_reminder(reminder_id)

    def clear_all_reminders(self) -> int:
        """Clear all reminders."""
        return self.db.clear_all_reminders()


# Global ReminderManager singleton
reminder_manager = ReminderManager()
