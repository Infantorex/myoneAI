"""Exponential backoff reconnection manager for Cloud Communication (Phase 12).

Provides controlled exponential backoff (2s -> 4s -> 8s -> 16s -> 32s -> max 60s) to prevent aggressive retry loops.
"""

import logging
import random
from typing import Optional

logger = logging.getLogger("myoneAI.cloud.reconnect")


class ReconnectManager:
    """Calculates backoff delays with exponential progression and upper bounds."""

    def __init__(
        self,
        min_interval: float = 2.0,
        max_interval: float = 60.0,
        factor: float = 2.0,
        jitter_ratio: float = 0.1,
    ) -> None:
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.factor = factor
        self.jitter_ratio = jitter_ratio
        self._attempts: int = 0
        self._current_delay: float = min_interval

    @property
    def attempts(self) -> int:
        """Return the number of consecutive failed connection attempts."""
        return self._attempts

    def get_next_delay(self) -> float:
        """Calculate the next sleep delay in seconds before retrying."""
        if self._attempts == 0:
            base_delay = self.min_interval
        else:
            base_delay = min(self.max_interval, self.min_interval * (self.factor ** self._attempts))

        # Add slight jitter (e.g. +/- 10%) to prevent lockstep retry storms
        if self.jitter_ratio > 0:
            jitter = base_delay * self.jitter_ratio * random.uniform(-1, 1)
            final_delay = max(self.min_interval, min(self.max_interval, base_delay + jitter))
        else:
            final_delay = base_delay

        return round(final_delay, 2)

    def record_failure(self) -> float:
        """Increment failure counter and return calculated backoff delay."""
        delay = self.get_next_delay()
        self._attempts += 1
        logger.debug("Cloud connection failure #%d. Backing off for %.2fs.", self._attempts, delay)
        return delay

    def record_success(self) -> None:
        """Reset backoff state after a successful connection."""
        if self._attempts > 0:
            logger.info("Cloud connection established. Resetting backoff counters.")
        self._attempts = 0
        self._current_delay = self.min_interval

    def reset(self) -> None:
        """Explicitly reset attempt counter."""
        self._attempts = 0
        self._current_delay = self.min_interval
