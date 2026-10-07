"""Lightweight wake-word detection interface.

Ensures zero continuous heavy audio processing on 8GB RAM / i3 CPU.
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional

from app.voice.wakeword_provider import (
    BaseWakeWordProvider,
    LocalWakeWordProvider,
    MockWakeWordProvider,
    get_wakeword_provider,
)


class BaseWakeWord(ABC):
    """Abstract base class for lightweight wake word engines."""

    @abstractmethod
    def start_listening(self, on_detected: Callable[[], None]) -> None:
        """Start low-power background detection for the wake word."""
        pass

    @abstractmethod
    def stop_listening(self) -> None:
        """Stop wake word detection and release audio resources."""
        pass


__all__ = [
    "BaseWakeWord",
    "BaseWakeWordProvider",
    "LocalWakeWordProvider",
    "MockWakeWordProvider",
    "get_wakeword_provider",
]
