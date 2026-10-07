"""Web browsing and search tools.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("myoneAI.tools.browser")


def open_website(url: str) -> Dict[str, Any]:
    """Open a URL in the user's default browser."""
    logger.info("Opening website URL: %s", url)
    return {"success": True, "action": "open_website", "url": url}


def search_web(query: str) -> Dict[str, Any]:
    """Search Google or default search engine."""
    logger.info("Searching web for: %s", query)
    return {"success": True, "action": "search_web", "query": query}
