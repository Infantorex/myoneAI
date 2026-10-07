"""Schemas for Vercel Cloud Control Plane API (Phase 12).

Provides validation models for cloud endpoints handling device registration, heartbeats, and commands.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CloudRegisterRequest(BaseModel):
    """Device registration payload sent from laptop."""
    id: str
    type: str = "register"
    timestamp: float
    device_id: str
    payload: Dict[str, Any]
    signature: Optional[str] = None


class CloudHeartbeatRequest(BaseModel):
    """Periodic telemetry payload sent from laptop."""
    id: str
    type: str = "heartbeat"
    timestamp: float
    device_id: str
    payload: Dict[str, Any]
    signature: Optional[str] = None


class CloudCommandRequest(BaseModel):
    """Command payload dispatched to or returned from laptop."""
    id: str
    type: str = "command"
    timestamp: float
    device_id: str
    payload: Dict[str, Any]
    status: Optional[str] = None
    signature: Optional[str] = None


class CloudDeviceStatusResponse(BaseModel):
    """Device online/offline state and telemetry summary."""
    device_id: str
    device_name: str
    device_version: str
    status: str
    last_seen: float
    last_seen_iso: str
    telemetry: Dict[str, Any] = Field(default_factory=dict)
