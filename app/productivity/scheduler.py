"""Background scheduler for due reminders, missed reminders, and startup recovery (Phase 10)."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from app.core.config import Settings, get_settings
from app.core.events import EventBus, event_bus
from app.productivity.database import ProductivityDatabase, productivity_db
from app.productivity.models import RecurrenceRule, ReminderItem, ReminderStatus
from app.productivity.reminders import ReminderManager, reminder_manager

logger = logging.getLogger("myoneAI.productivity.scheduler")


class ProductivityScheduler:
    """Lightweight periodic scheduler checking and triggering due reminders."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        db: Optional[ProductivityDatabase] = None,
        reminder_mgr: Optional[ReminderManager] = None,
        event_bus_instance: Optional[EventBus] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.db = db or productivity_db
        self.reminder_manager = reminder_mgr or reminder_manager
        self.event_bus = event_bus_instance or event_bus
        self._task: Optional[asyncio.Task] = None
        self._is_running: bool = False
        self._handlers: List[Callable[[ReminderItem], None]] = []

    @property
    def check_interval(self) -> int:
        """Configured background check interval in seconds (default 30)."""
        return max(5, int(getattr(self.settings, "productivity_check_interval", 30)))

    @property
    def max_missed_on_startup(self) -> int:
        """Maximum past due reminders to trigger upon restart."""
        return int(getattr(self.settings, "max_missed_reminders_on_startup", 5))

    @property
    def is_running(self) -> bool:
        """True if the background loop is active."""
        return self._is_running

    def register_handler(self, handler: Callable[[ReminderItem], None]) -> None:
        """Register a notification callback for triggered reminders."""
        if handler not in self._handlers:
            self._handlers.append(handler)

    def recover_on_startup(self) -> Dict[str, Any]:
        """Check for reminders that became due while JARVIS was offline.

        Returns:
            Dictionary with recovered_count, triggered_reminders, and skipped_count.
        """
        now_iso = datetime.now().isoformat()
        missed = self.db.get_due_reminders(now_iso)

        if not missed:
            logger.debug("No missed reminders found on startup.")
            return {"recovered_count": 0, "triggered": [], "skipped_count": 0}

        logger.info("Found %d pending reminders due before now.", len(missed))

        to_trigger = missed[:self.max_missed_on_startup]
        to_skip = missed[self.max_missed_on_startup:]

        triggered_items = []
        for rem in to_trigger:
            self._dispatch_reminder(rem)
            triggered_items.append(rem)

        # Mark excessive old missed reminders as completed/skipped to prevent flooding
        for rem in to_skip:
            logger.warning("Skipping old missed reminder #%s: '%s' (exceeded startup limit of %d)", rem.id, rem.message, self.max_missed_on_startup)
            if rem.id is not None:
                self.db.update_reminder_status(rem.id, status=ReminderStatus.COMPLETED)

        return {
            "recovered_count": len(triggered_items),
            "triggered": [r.to_dict() for r in triggered_items],
            "skipped_count": len(to_skip),
        }

    def check_reminders_sync(self) -> List[ReminderItem]:
        """Synchronously check and trigger due reminders."""
        now_iso = datetime.now().isoformat()
        due_items = self.db.get_due_reminders(now_iso)
        triggered = []

        for rem in due_items:
            self._dispatch_reminder(rem)
            triggered.append(rem)

        return triggered

    async def check_reminders(self) -> List[ReminderItem]:
        """Asynchronously check and trigger due reminders."""
        return await asyncio.to_thread(self.check_reminders_sync)

    def _dispatch_reminder(self, rem: ReminderItem) -> None:
        """Mark reminder triggered and notify subscribers."""
        if rem.id is not None:
            self.reminder_manager.complete_reminder(rem.id)

        logger.info("TRIGGERED Reminder #%s: '%s'", rem.id, rem.message)

        # Event Bus notification
        if self.event_bus:
            self.event_bus.emit("reminder.triggered", rem.to_dict())

        # Callback handlers
        for handler in self._handlers:
            try:
                handler(rem)
            except Exception as exc:
                logger.error("Error executing reminder handler %s: %s", handler, exc)

    async def _scheduler_loop(self) -> None:
        """Periodic background evaluation loop."""
        logger.info("ProductivityScheduler loop started (interval=%ds)", self.check_interval)

        # Startup recovery on loop enter
        try:
            self.recover_on_startup()
        except Exception as exc:
            logger.error("Error during startup reminder recovery: %s", exc)

        while self._is_running:
            try:
                await self.check_reminders()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error checking reminders in scheduler loop: %s", exc, exc_info=True)

            try:
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break

        logger.info("ProductivityScheduler loop stopped")

    def start(self) -> bool:
        """Start the background reminder checker."""
        if not getattr(self.settings, "productivity_enabled", True):
            logger.info("Productivity system is disabled by config (PRODUCTIVITY_ENABLED=false)")
            return False

        if self._is_running:
            return True

        self._is_running = True
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._scheduler_loop())
            return True
        except RuntimeError:
            logger.warning("No active asyncio loop available to start scheduler")
            self._is_running = False
            return False

    def stop(self) -> None:
        """Stop the background scheduler loop."""
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None


# Global Scheduler singleton
productivity_scheduler = ProductivityScheduler()
