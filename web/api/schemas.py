"""Pydantic data schemas for myoneAI Web Dashboard API (Phase 11).

Provides strictly-typed request validation and response models.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# -----------------------------------------------------------------------------
# Common / Generic Models
# -----------------------------------------------------------------------------

class APIErrorDetail(BaseModel):
    """Structured error payload."""
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error explanation")


class APIErrorResponse(BaseModel):
    """Standardized error response envelope."""
    success: bool = Field(default=False)
    error: APIErrorDetail


class APISuccessResponse(BaseModel):
    """Generic success envelope."""
    success: bool = Field(default=True)
    message: Optional[str] = None


# -----------------------------------------------------------------------------
# System Telemetry Schemas
# -----------------------------------------------------------------------------

class SystemStatusResponse(BaseModel):
    """System health snapshot for the dashboard."""
    cpu_percent: float = Field(..., ge=0, le=100, description="CPU usage percentage")
    memory_percent: float = Field(..., ge=0, le=100, description="RAM usage percentage")
    disk_percent: float = Field(..., ge=0, le=100, description="Primary disk usage percentage")
    battery_percent: Optional[float] = Field(None, ge=0, le=100, description="Battery level if available")
    battery_plugged: Optional[bool] = Field(None, description="True if power adapter plugged in")
    network_available: bool = Field(..., description="Internet / gateway reachability")


class TopProcessItem(BaseModel):
    """Lightweight process metric item."""
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_mb: float


class SystemDiagnosisResponse(BaseModel):
    """Deep system diagnosis response."""
    status: str
    warnings: List[str] = Field(default_factory=list)
    top_cpu_processes: List[TopProcessItem] = Field(default_factory=list)
    top_memory_processes: List[TopProcessItem] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# Assistant State & Control Schemas
# -----------------------------------------------------------------------------

class AssistantStatusResponse(BaseModel):
    """Assistant execution status."""
    state: str = Field(..., description="Current state: idle, listening, thinking, speaking, error")
    wake_word_enabled: bool = Field(default=True)
    voice_enabled: bool = Field(default=True)
    uptime_seconds: Optional[float] = None


class AssistantControlRequest(BaseModel):
    """Action command for assistant lifecycle."""
    action: Optional[str] = Field(default="start", description="Control action (start/stop)")


# -----------------------------------------------------------------------------
# Chat Schemas
# -----------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Incoming user text chat request."""
    message: str = Field(..., min_length=1, max_length=2000, description="Spoken or typed user prompt")


class ChatResponse(BaseModel):
    """Assistant conversational response."""
    success: bool = Field(default=True)
    response: str = Field(..., description="Assistant text response")
    timestamp: Optional[str] = None


# -----------------------------------------------------------------------------
# Memory Schemas
# -----------------------------------------------------------------------------

class MemoryItemResponse(BaseModel):
    """Structured memory entry for dashboard table."""
    id: Optional[str] = None
    category: str
    key: str
    value: str
    confidence: float = 1.0
    updated: str
    created_at: Optional[str] = None


class MemoryCreateRequest(BaseModel):
    """Request to record a user memory fact."""
    category: str = Field(..., min_length=1, max_length=64)
    key: str = Field(..., min_length=1, max_length=128)
    value: str = Field(..., min_length=1, max_length=2000)


class MemoryStatsResponse(BaseModel):
    """Memory store overview statistics."""
    total_memories: int
    categories: Dict[str, int] = Field(default_factory=dict)


class MemoryClearRequest(BaseModel):
    """Confirmation payload to clear all memories."""
    confirmed: bool = Field(..., description="Explicit confirmation boolean")


# -----------------------------------------------------------------------------
# Productivity Schemas (Tasks, Reminders, Notes)
# -----------------------------------------------------------------------------

class TaskCreateRequest(BaseModel):
    """Create task request."""
    title: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = Field(default="", max_length=2000)
    priority: Optional[str] = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH, CRITICAL")
    due_at: Optional[str] = Field(default=None, description="ISO datetime string or natural phrase")


class TaskUpdateRequest(BaseModel):
    """Partial task update request."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=256)
    description: Optional[str] = Field(default=None, max_length=2000)
    priority: Optional[str] = None
    status: Optional[str] = None
    due_at: Optional[str] = None


class TaskResponse(BaseModel):
    """Task item response."""
    id: int
    title: str
    description: str
    priority: str
    status: str
    due_at: Optional[str] = None
    created_at: str
    updated_at: str


class ReminderCreateRequest(BaseModel):
    """Schedule reminder request."""
    message: str = Field(..., min_length=1, max_length=500)
    trigger_at: Optional[str] = Field(default=None, description="ISO datetime string or natural time")
    recurrence: Optional[str] = Field(default="NONE", description="NONE, DAILY, WEEKDAYS, WEEKLY, MONTHLY")


class ReminderResponse(BaseModel):
    """Reminder item response."""
    id: int
    message: str
    trigger_at: str
    status: str
    recurrence: str
    created_at: str


class NoteCreateRequest(BaseModel):
    """Create note request."""
    title: str = Field(..., min_length=1, max_length=256)
    content: str = Field(..., min_length=1, max_length=10000)
    tags: Optional[List[str]] = Field(default_factory=list)


class NoteUpdateRequest(BaseModel):
    """Update note request."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=256)
    content: Optional[str] = Field(default=None, max_length=10000)
    tags: Optional[List[str]] = None


class NoteResponse(BaseModel):
    """Note item response."""
    id: int
    title: str
    content: str
    tags: List[str]
    created_at: str
    updated_at: str


# -----------------------------------------------------------------------------
# Activity Feed & Settings Schemas
# -----------------------------------------------------------------------------

class ActivityEventResponse(BaseModel):
    """Safe, sanitized event item for the activity feed."""
    id: Optional[str] = None
    timestamp: str
    event_type: str
    description: str
    level: str = "INFO"


class SafeSettingsResponse(BaseModel):
    """Safe configuration parameters visible to frontend dashboard."""
    app_name: str
    version: str
    language: str
    web_host: str
    web_port: int
    web_auth_enabled: bool
    web_status_refresh_seconds: int
    web_chat_max_length: int
    monitoring_interval_seconds: int
    memory_enabled: bool
    productivity_enabled: bool
    tools_enabled: bool
