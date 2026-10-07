"""Settings API routes for myoneAI Web Dashboard (Phase 11).

Provides safe configuration parameters to the frontend without exposing secrets or paths.
"""

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from web.api.auth import require_auth
from web.api.schemas import SafeSettingsResponse

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=SafeSettingsResponse, dependencies=[Depends(require_auth)])
async def get_safe_settings(settings: Settings = Depends(get_settings)) -> SafeSettingsResponse:
    """Retrieve safe system configuration parameters."""
    return SafeSettingsResponse(
        app_name=settings.app_name,
        version=settings.app_version,
        language=settings.language,
        web_host=settings.web_host,
        web_port=settings.web_port,
        web_auth_enabled=settings.web_auth_enabled,
        web_status_refresh_seconds=settings.web_status_refresh_seconds,
        web_chat_max_length=settings.web_chat_max_length,
        monitoring_interval_seconds=settings.monitoring_interval_seconds,
        memory_enabled=settings.memory_enabled,
        productivity_enabled=settings.productivity_enabled,
        tools_enabled=settings.tools_enabled,
        cloud_enabled=settings.cloud_enabled,
        cloud_device_id=settings.cloud_device_id,
        cloud_api_url=settings.cloud_api_url,
    )
