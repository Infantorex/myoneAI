"""Vercel Cloud Control Plane REST API Endpoints (Phase 12).

Provides endpoints for device registration, heartbeat intake, telemetry inspection,
and secure asynchronous command dispatch.
"""

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from web.cloud.auth import require_cloud_auth
from web.cloud.devices import cloud_device_registry
from web.cloud.schemas import (
    CloudCommandRequest,
    CloudDeviceStatusResponse,
    CloudHeartbeatRequest,
    CloudRegisterRequest,
)

logger = logging.getLogger("myoneAI.cloud.api.routes")

cloud_router = APIRouter(prefix="/api/device", tags=["Cloud Control Plane"])


@cloud_router.post("/register", dependencies=[Depends(require_cloud_auth)])
async def register_device(payload: CloudRegisterRequest) -> Dict[str, Any]:
    """Register laptop device identity with Cloud Control Plane."""
    dev = cloud_device_registry.register_device(payload.device_id, payload.payload)
    return {
        "success": True,
        "message": f"Device '{payload.device_id}' registered successfully.",
        "device": dev,
    }


@cloud_router.post("/heartbeat", dependencies=[Depends(require_cloud_auth)])
async def record_heartbeat(payload: CloudHeartbeatRequest) -> Dict[str, Any]:
    """Receive periodic telemetry heartbeat from laptop."""
    dev = cloud_device_registry.record_heartbeat(payload.device_id, payload.payload)
    return {
        "success": True,
        "status": "ack",
        "device_id": payload.device_id,
        "timestamp": datetime.now().isoformat(),
    }


@cloud_router.get("/status", dependencies=[Depends(require_cloud_auth)])
async def get_device_status(device_id: str = Query(..., description="Device ID to query")) -> Dict[str, Any]:
    """Query live online/offline state and latest telemetry of a registered device."""
    dev = cloud_device_registry.get_device_status(device_id)
    if not dev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "DEVICE_NOT_FOUND",
                    "message": f"Device '{device_id}' is not registered with Cloud Control Plane.",
                },
            },
        )
    return {
        "success": True,
        "device": dev,
    }


@cloud_router.get("/list", dependencies=[Depends(require_cloud_auth)])
async def list_devices() -> Dict[str, Any]:
    """List all registered devices on the control plane."""
    devices = cloud_device_registry.list_devices()
    return {
        "success": True,
        "devices": devices,
    }


@cloud_router.post("/request", dependencies=[Depends(require_cloud_auth)])
async def dispatch_or_poll_request(
    payload: Optional[CloudCommandRequest] = None,
    device_id: Optional[str] = Query(None, description="Device ID polling for pending commands"),
) -> Dict[str, Any]:
    """Dispatch a command to a device, or allow a laptop to poll its pending commands."""
    # 1. Laptop polling for commands
    if device_id and not payload:
        commands = cloud_device_registry.get_pending_commands(device_id)
        return {
            "success": True,
            "device_id": device_id,
            "commands": commands,
        }

    # 2. Vercel dashboard dispatching command to laptop
    if payload:
        cloud_device_registry.queue_command(payload.device_id, payload.model_dump())
        return {
            "success": True,
            "message": f"Command '{payload.id}' queued for device '{payload.device_id}'.",
            "command_id": payload.id,
        }

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"success": False, "error": {"code": "BAD_REQUEST", "message": "Invalid request payload."}},
    )


@cloud_router.post("/response", dependencies=[Depends(require_cloud_auth)])
async def record_command_response(payload: CloudCommandRequest) -> Dict[str, Any]:
    """Receive command execution outcome from laptop."""
    cloud_device_registry.record_response(payload.id, payload.model_dump())
    return {
        "success": True,
        "message": f"Response for command '{payload.id}' recorded.",
    }


@cloud_router.post("/disconnect", dependencies=[Depends(require_cloud_auth)])
async def disconnect_device(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Explicitly mark device as disconnected."""
    device_id = payload.get("device_id", "")
    if device_id:
        cloud_device_registry.disconnect_device(device_id)
    return {
        "success": True,
        "message": f"Device '{device_id}' disconnected.",
    }
