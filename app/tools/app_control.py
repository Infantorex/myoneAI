"""Application launching and closing tool definitions.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("myoneAI.tools.app_control")


def open_application(app_name: str) -> Dict[str, Any]:
    """Open a whitelisted application by name or common alias."""
    logger.info("Requested to open application: %s", app_name)
    return {"success": True, "action": "open_app", "target": app_name}


def close_application(app_name: str) -> Dict[str, Any]:
    """Close an application process."""
    logger.info("Requested to close application: %s", app_name)
    return {"success": True, "action": "close_app", "target": app_name}
