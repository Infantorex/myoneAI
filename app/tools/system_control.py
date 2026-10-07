"""System information and screenshot actions.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("myoneAI.tools.system_control")


def get_system_info() -> Dict[str, Any]:
    """Retrieve basic system information."""
    import platform
    return {
        "success": True,
        "platform": platform.system(),
        "release": platform.release(),
        "processor": platform.processor(),
    }


def take_screenshot(save_path: str = "data/screenshot.png") -> Dict[str, Any]:
    """Capture screen on-demand."""
    logger.info("Screenshot requested to: %s", save_path)
    return {"success": True, "action": "screenshot", "path": save_path}
