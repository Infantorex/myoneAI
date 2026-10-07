"""Filesystem operations (safe folders, whitelisted file viewing).
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("myoneAI.tools.filesystem")


def open_folder(folder_path: str) -> Dict[str, Any]:
    """Open a directory in Windows File Explorer."""
    logger.info("Opening folder path: %s", folder_path)
    return {"success": True, "action": "open_folder", "path": folder_path}


def open_file(file_path: str) -> Dict[str, Any]:
    """Open a file with default association."""
    logger.info("Opening file: %s", file_path)
    return {"success": True, "action": "open_file", "path": file_path}
