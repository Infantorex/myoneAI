"""Unified entrypoint for the Wake Word Subsystem (Phase 6).

Exports providers, manager, state enums, and singleton instances.
"""

from app.voice.wakeword_manager import (
    WakeWordManager,
    WakeWordState,
    wake_word_manager,
)
from app.voice.wakeword_provider import (
    BaseWakeWordProvider,
    LocalWakeWordProvider,
    MockWakeWordProvider,
    get_wakeword_provider,
)

__all__ = [
    "BaseWakeWordProvider",
    "LocalWakeWordProvider",
    "MockWakeWordProvider",
    "get_wakeword_provider",
    "WakeWordManager",
    "WakeWordState",
    "wake_word_manager",
]
