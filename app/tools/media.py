"""Media and audio volume control tools.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("myoneAI.tools.media")


def set_volume(level_percent: int) -> Dict[str, Any]:
    """Adjust system volume level (0-100)."""
    level_percent = max(0, min(100, level_percent))
    logger.info("Setting volume to %d%%", level_percent)
    return {"success": True, "action": "set_volume", "level": level_percent}


def play_pause_media() -> Dict[str, Any]:
    """Toggle media play / pause."""
    logger.info("Toggling media playback")
    return {"success": True, "action": "play_pause"}
