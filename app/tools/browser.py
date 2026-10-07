"""Browser and web navigation tools for myoneAI (Phase 8).

Opens web pages and search queries strictly using approved HTTP/HTTPS schemes.
"""

import logging
import urllib.parse
import webbrowser
from typing import Any, Dict

from app.security.policies import is_url_allowed
from app.tools.schemas import ToolResult

logger = logging.getLogger("myoneAI.tools.browser")


def open_website(url: str) -> ToolResult:
    """Open an allowlisted HTTP/HTTPS URL in the default web browser."""
    clean_url = url.strip()
    if not is_url_allowed(clean_url):
        return ToolResult(
            success=False,
            tool="open_website",
            message=f"Access to URL scheme or destination is restricted: '{url}'",
            error="Forbidden URL scheme or format.",
        )

    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url


    logger.info("Opening URL in browser: '%s'", clean_url)
    try:
        webbrowser.open(clean_url)
        return ToolResult(
            success=True,
            tool="open_website",
            message=f"Website open பண்ணிட்டேன் ({clean_url}).",
            data={"url": clean_url},
        )
    except Exception as exc:
        logger.error("Failed to open browser URL '%s': %s", clean_url, exc)
        return ToolResult(
            success=False,
            tool="open_website",
            message=f"Failed to open website: {exc}",
            error=str(exc),
        )


def search_web_browser(query: str) -> ToolResult:
    """Perform a web search query via Google in the default browser."""
    clean_query = query.strip()
    if not clean_query:
        return ToolResult(
            success=False,
            tool="search_web_browser",
            message="Search query cannot be empty.",
            error="Empty query provided.",
        )

    encoded = urllib.parse.quote_plus(clean_query)
    search_url = f"https://www.google.com/search?q={encoded}"

    logger.info("Searching web in browser: '%s'", clean_query)
    try:
        webbrowser.open(search_url)
        return ToolResult(
            success=True,
            tool="search_web_browser",
            message=f"Google-ல் தேடுகிறேன்: '{clean_query}'.",
            data={"query": clean_query, "url": search_url},
        )
    except Exception as exc:
        logger.error("Failed to execute browser search '%s': %s", clean_query, exc)
        return ToolResult(
            success=False,
            tool="search_web_browser",
            message=f"Search failed: {exc}",
            error=str(exc),
        )
