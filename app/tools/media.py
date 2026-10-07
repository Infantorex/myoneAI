"""Lightweight media and system audio controls for myoneAI (Phase 8).

Controls volume and media playback directly using native OS virtual key events (zero subprocesses).
"""

import ctypes
import logging
import sys
from typing import Any, Dict

from app.tools.schemas import ToolResult

logger = logging.getLogger("myoneAI.tools.media")

# Windows Virtual Key Codes for Media & Volume
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


def _send_win_key(vk_code: int, count: int = 1) -> None:
    """Send Windows key down + key up event via user32."""
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        for _ in range(count):
            user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
            user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
    except Exception as exc:
        logger.debug("Failed to send virtual key 0x%02X: %s", vk_code, exc)


def volume_up(step_percent: int = 10) -> ToolResult:
    """Increase system audio volume."""
    # Each VK_VOLUME_UP step in Windows adjusts ~2% volume
    press_count = max(1, step_percent // 2)
    _send_win_key(VK_VOLUME_UP, count=press_count)
    logger.info("Volume increased by ~%d%%", step_percent)
    return ToolResult(
        success=True,
        tool="volume_up",
        message="Volume அதிகரித்துள்ளேன் (Volume increased).",
        data={"step_percent": step_percent},
    )


def volume_down(step_percent: int = 10) -> ToolResult:
    """Decrease system audio volume."""
    press_count = max(1, step_percent // 2)
    _send_win_key(VK_VOLUME_DOWN, count=press_count)
    logger.info("Volume decreased by ~%d%%", step_percent)
    return ToolResult(
        success=True,
        tool="volume_down",
        message="Volume குறைத்துள்ளேன் (Volume decreased).",
        data={"step_percent": step_percent},
    )


def set_volume(volume_percent: int = 50) -> ToolResult:
    """Set approximate target volume."""
    clamped = max(0, min(100, volume_percent))
    # First mute/zero, then step up
    _send_win_key(VK_VOLUME_DOWN, count=50)
    _send_win_key(VK_VOLUME_UP, count=clamped // 2)
    return ToolResult(
        success=True,
        tool="set_volume",
        message=f"Volume set to ~{clamped}%.",
        data={"target_volume_percent": clamped},
    )


def toggle_mute() -> ToolResult:
    """Toggle system audio mute on/off."""
    _send_win_key(VK_VOLUME_MUTE, count=1)
    logger.info("Toggled system mute.")
    return ToolResult(
        success=True,
        tool="toggle_mute",
        message="Audio mute toggled (மாற்றப்பட்டது).",
    )


def media_play_pause() -> ToolResult:
    """Toggle Play / Pause for active media player."""
    _send_win_key(VK_MEDIA_PLAY_PAUSE, count=1)
    logger.info("Toggled media play/pause.")
    return ToolResult(
        success=True,
        tool="media_play_pause",
        message="Media Play/Pause toggled.",
    )


def media_next() -> ToolResult:
    """Skip to next media track."""
    _send_win_key(VK_MEDIA_NEXT_TRACK, count=1)
    logger.info("Skipped to next media track.")
    return ToolResult(
        success=True,
        tool="media_next",
        message="Next track (அடுத்த பாடல்).",
    )


def media_previous() -> ToolResult:
    """Return to previous media track."""
    _send_win_key(VK_MEDIA_PREV_TRACK, count=1)
    logger.info("Returned to previous media track.")
    return ToolResult(
        success=True,
        tool="media_previous",
        message="Previous track (முந்தைய பாடல்).",
    )
