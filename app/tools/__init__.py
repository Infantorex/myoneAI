"""PC Tools and Action execution interfaces for myoneAI.
"""

from app.tools.app_control import open_application, close_application
from app.tools.browser import open_website, search_web
from app.tools.filesystem import open_folder, open_file
from app.tools.system_control import get_system_info, take_screenshot
from app.tools.media import set_volume, play_pause_media

__all__ = [
    "open_application",
    "close_application",
    "open_website",
    "search_web",
    "open_folder",
    "open_file",
    "get_system_info",
    "take_screenshot",
    "set_volume",
    "play_pause_media",
]
