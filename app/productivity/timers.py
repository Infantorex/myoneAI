"""In-memory lightweight async countdown timer engine (Phase 10)."""

import asyncio
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from app.core.config import Settings, get_settings
from app.core.events import EventBus, event_bus
from app.productivity.models import ActiveTimer, TimerStatus

logger = logging.getLogger("myoneAI.productivity.timers")


class TimerManager:
    """Manages active in-memory countdown timers with async expiration callbacks."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        event_bus_instance: Optional[EventBus] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.event_bus = event_bus_instance or event_bus
        self._timers: Dict[str, ActiveTimer] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._callbacks: List[Callable[[ActiveTimer], None]] = []

    @property
    def max_active_timers(self) -> int:
        """Maximum concurrent running timers."""
        return int(getattr(self.settings, "max_active_timers", 5))

    def register_callback(self, callback: Callable[[ActiveTimer], None]) -> None:
        """Register a callback handler to be invoked on timer completion."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def create_timer(
        self,
        duration_seconds: float,
        label: str = "Timer",
    ) -> ActiveTimer:
        """Create and start a new countdown timer.

        Args:
            duration_seconds: Countdown duration in seconds.
            label: Friendly label or description (e.g. 'Pasta timer', 'Meeting prep').

        Returns:
            ActiveTimer instance.
        """
        if duration_seconds <= 0:
            raise ValueError("Timer duration must be greater than 0 seconds.")

        # Clean up already completed timers
        self._cleanup_finished()

        active_count = len([t for t in self._timers.values() if t.status == TimerStatus.RUNNING])
        if active_count >= self.max_active_timers:
            raise RuntimeError(f"Maximum active timers limit reached ({self.max_active_timers}). Please cancel an existing timer.")

        timer_id = str(uuid.uuid4())[:8]
        now = time.time()
        timer = ActiveTimer(
            id=timer_id,
            label=label.strip() or "Timer",
            duration_seconds=duration_seconds,
            start_time=now,
            end_time=now + duration_seconds,
            status=TimerStatus.RUNNING,
        )

        self._timers[timer_id] = timer

        # Start async countdown task if loop is running
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._countdown_worker(timer_id, duration_seconds))
            self._tasks[timer_id] = task
        except RuntimeError:
            logger.debug("No running asyncio event loop available; timer stored synchronously")

        logger.info("Started Timer '%s' [%s] for %.1f seconds", timer.label, timer.id, duration_seconds)
        return timer

    async def _countdown_worker(self, timer_id: str, duration: float) -> None:
        """Asynchronously wait for timer expiration and trigger notifications."""
        try:
            await asyncio.sleep(duration)
            timer = self._timers.get(timer_id)
            if timer and timer.status == TimerStatus.RUNNING:
                timer.status = TimerStatus.COMPLETED
                logger.info("Timer '%s' [%s] completed!", timer.label, timer.id)

                # Emit completion event
                if self.event_bus:
                    self.event_bus.emit("timer.completed", timer.to_dict())

                # Notify registered callbacks
                for cb in self._callbacks:
                    try:
                        cb(timer)
                    except Exception as exc:
                        logger.error("Error in timer callback: %s", exc)
        except asyncio.CancelledError:
            pass

    def get_timer(self, timer_id: str) -> Optional[ActiveTimer]:
        """Fetch timer by ID."""
        return self._timers.get(timer_id)

    def get_active_timers(self) -> List[ActiveTimer]:
        """Return all currently running timers."""
        self._cleanup_finished()
        return [t for t in self._timers.values() if t.status == TimerStatus.RUNNING]

    def get_latest_timer(self) -> Optional[ActiveTimer]:
        """Get the most recently created active timer."""
        active = self.get_active_timers()
        return active[-1] if active else None

    def cancel_timer(self, timer_id: Optional[str] = None) -> Optional[ActiveTimer]:
        """Cancel an active timer by ID or the most recent one if ID is omitted."""
        if not timer_id:
            latest = self.get_latest_timer()
            if not latest:
                return None
            timer_id = latest.id

        timer = self._timers.get(timer_id)
        if not timer:
            return None

        timer.status = TimerStatus.CANCELLED
        task = self._tasks.get(timer_id)
        if task and not task.done():
            task.cancel()

        logger.info("Cancelled Timer '%s' [%s]", timer.label, timer.id)
        return timer

    def clear_all_timers(self) -> int:
        """Cancel and remove all timers."""
        count = 0
        for tid, task in self._tasks.items():
            if not task.done():
                task.cancel()
            count += 1
        self._timers.clear()
        self._tasks.clear()
        return count

    def _cleanup_finished(self) -> None:
        """Prune long expired completed or cancelled timers."""
        now = time.time()
        to_remove = []
        for tid, timer in self._timers.items():
            if timer.status == TimerStatus.RUNNING and now >= timer.end_time:
                timer.status = TimerStatus.COMPLETED
            if timer.status in (TimerStatus.COMPLETED, TimerStatus.CANCELLED) and (now - timer.end_time) > 60:
                to_remove.append(tid)

        for tid in to_remove:
            self._timers.pop(tid, None)
            self._tasks.pop(tid, None)


# Global TimerManager singleton
timer_manager = TimerManager()
