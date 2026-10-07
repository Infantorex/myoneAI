"""Authentication dependency and token validation for myoneAI Web Dashboard (Phase 11).

Provides local token authentication with constant-time verification.
If WEB_AUTH_ENABLED is False (development mode), all requests are accepted.
"""

import logging
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Query, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import Settings, get_settings

logger = logging.getLogger("myoneAI.web.auth")

# Optional HTTPBearer scheme so browser / swagger UI can provide Bearer tokens
bearer_scheme = HTTPBearer(auto_error=False)


def get_token_from_request(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    token_query: Optional[str] = Query(None, alias="token"),
) -> Optional[str]:
    """Extract token from Authorization header or URL query parameter."""
    if credentials and credentials.credentials:
        return credentials.credentials
    if token_query:
        return token_query
    return None


def require_auth(
    token: Optional[str] = Depends(get_token_from_request),
    settings: Settings = Depends(get_settings),
) -> bool:
    """Validate incoming request against configured WEB_AUTH_TOKEN.

    If WEB_AUTH_ENABLED is False, access is unconditionally granted (development mode).
    If WEB_AUTH_ENABLED is True, a matching token is required.

    Raises:
        HTTPException: 401 Unauthorized if token is missing or invalid.
    """
    if not settings.web_auth_enabled:
        return True

    expected_token = settings.web_auth_token.strip() if settings.web_auth_token else ""
    if not expected_token:
        # Auth is enabled but no secret token is configured in .env -> allow or warn
        logger.warning("WEB_AUTH_ENABLED is True, but WEB_AUTH_TOKEN is empty. Requests will be rejected.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "AUTH_CONFIG_ERROR",
                    "message": "WEB_AUTH_TOKEN is not configured on the server.",
                },
            },
        )

    if not token or not secrets.compare_digest(token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid or missing authentication token.",
                },
            },
        )

    return True
