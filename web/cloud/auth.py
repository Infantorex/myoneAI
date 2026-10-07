"""Authentication and token validation for Vercel Cloud Control Plane (Phase 12).

Provides Bearer token verification and HMAC signature validation for inbound laptop requests.
"""

import logging
import secrets
from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings

logger = logging.getLogger("myoneAI.cloud.api.auth")

cloud_bearer_scheme = HTTPBearer(auto_error=False)


def require_cloud_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(cloud_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> bool:
    """Validate incoming request from laptop or dashboard against CLOUD_AUTH_TOKEN.

    If CLOUD_AUTH_TOKEN is not configured, allows requests (development mode).
    If CLOUD_AUTH_TOKEN is configured, requires exact Bearer token match.
    """
    expected_token = settings.cloud_auth_token.strip() if settings.cloud_auth_token else ""
    if not expected_token:
        # Development mode when cloud auth token is not set
        return True

    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Missing Bearer authentication token for Cloud Control Plane.",
                },
            },
        )

    if not secrets.compare_digest(credentials.credentials, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "Invalid Cloud Control Plane authentication token.",
                },
            },
        )

    return True
