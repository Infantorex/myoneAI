"""Alert manager and cooldown engine for system health notifications (Phase 9).

Dispatches alerts, integrates with EventBus, and prevents notification spam
via configurable cooldown periods.
"""

import logging
import time
from collections import deque
from typing import Callable, Deque, Dict, List, Optional

from app.core.config import Settings, get_settings
from app.monitoring.models import AlertLevel, SystemAlert

logger = logging.getLogger("myoneAI.monitoring.alerts")


class AlertManager:
    """Manages system health alerts, cooldown suppression, and notification dispatch."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._last_alert_times: Dict[str, float] = {}
        self._handlers: List[Callable[[SystemAlert], None]] = []
        self._history: Deque[SystemAlert] = deque(maxlen=50)

    @property
    def cooldown_seconds(self) -> float:
        """Configured cooldown duration in seconds."""
        return float(getattr(self.settings, "alert_cooldown_seconds", 300))

    def register_handler(self, handler: Callable[[SystemAlert], None]) -> None:
        """Register a callback function to receive newly triggered alerts."""
        if handler not in self._handlers:
            self._handlers.append(handler)

    def unregister_handler(self, handler: Callable[[SystemAlert], None]) -> None:
        """Remove a registered alert callback handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)

    def should_suppress(self, alert: SystemAlert, current_time: Optional[float] = None) -> bool:
        """Determine if an alert is currently in cooldown suppression.

        Args:
            alert: SystemAlert candidate.
            current_time: Optional epoch timestamp override.

        Returns:
            True if duplicate alert should be suppressed; False if it should fire.
        """
        now = current_time if current_time is not None else time.time()
        key = f"{alert.category}:{alert.level.value}"
        last_time = self._last_alert_times.get(key)

        if last_time is not None and (now - last_time) < self.cooldown_seconds:
            logger.debug(
                "Suppressing alert %s (cooldown active: %.1fs remaining)",
                key,
                self.cooldown_seconds - (now - last_time),
            )
            return True

        return False

    def process_alerts(
        self,
        alerts: List[SystemAlert],
        current_time: Optional[float] = None,
    ) -> List[SystemAlert]:
        """Filter alerts through cooldown deduplication and dispatch unsuppressed alerts.

        Args:
            alerts: Raw alerts from ThresholdEngine.
            current_time: Optional epoch timestamp override for testing.

        Returns:
            List of dispatched (unsuppressed) SystemAlert instances.
        """
        now = current_time if current_time is not None else time.time()
        dispatched: List[SystemAlert] = []

        for alert in alerts:
            if not self.should_suppress(alert, current_time=now):
                key = f"{alert.category}:{alert.level.value}"
                self._last_alert_times[key] = now
                self._history.append(alert)
                dispatched.append(alert)

                logger.warning(
                    "System Health Alert [%s] %s: %s",
                    alert.level.value,
                    alert.category.upper(),
                    alert.message,
                )

                # Notify registered handlers
                for handler in self._handlers:
                    try:
                        handler(alert)
                    except Exception as exc:
                        logger.error("Error executing alert handler %s: %s", handler, exc)

        return dispatched

    def get_recent_alerts(self, limit: int = 10) -> List[SystemAlert]:
        """Return the most recent dispatched alerts."""
        return list(self._history)[-limit:]

    def clear_cooldowns(self) -> None:
        """Reset cooldown timestamps (primarily for testing)."""
        self._last_alert_times.clear()

    def reset(self) -> None:
        """Clear all cooldowns, handlers, and history."""
        self._last_alert_times.clear()
        self._handlers.clear()
        self._history.clear()


# Global AlertManager singleton
alert_manager = AlertManager()
