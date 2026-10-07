"""Tool schemas, models, and structured results for PC Assistant Tools (Phase 8)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.security.permissions import PermissionLevel


class ToolError(Exception):
    """Base exception for all tool-related errors."""
    pass


class ToolNotFoundError(ToolError):
    """Raised when an unregistered tool is requested."""
    pass


class ToolPermissionDeniedError(ToolError):
    """Raised when an action is blocked by security policies."""
    pass


class ToolTimeoutError(ToolError):
    """Raised when a tool execution exceeds its timeout threshold."""
    pass


class ToolValidationError(ToolError):
    """Raised when tool arguments fail parameter validation."""
    pass


class ToolExecutionError(ToolError):
    """Raised when an error occurs during tool handler execution."""
    pass


class ToolSchema(BaseModel):
    """Definition of an allowlisted PC tool."""
    name: str = Field(..., description="Unique tool identifier name")
    description: str = Field(..., description="Human and AI readable description of capability")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="JSON Schema parameter specifications")
    required_params: List[str] = Field(default_factory=list, description="List of required parameter names")
    permission: PermissionLevel = Field(default=PermissionLevel.SAFE, description="Security permission tier")
    timeout_sec: float = Field(default=10.0, description="Max execution duration in seconds")

    def to_prompt_desc(self) -> str:
        """Format as a concise schema line for AI prompt injection."""
        param_desc = ", ".join(f"{k}: {v.get('type', 'any')}" for k, v in self.parameters.items())
        return f"- `{self.name}({param_desc})`: {self.description}"


class ToolCall(BaseModel):
    """Structured intent representing a tool invocation request."""
    tool: str = Field(..., description="Name of the tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments dictionary")


class ToolResult(BaseModel):
    """Structured output returned by tool execution."""
    success: bool = Field(..., description="Whether tool executed successfully")
    tool: str = Field(..., description="Tool name executed")
    message: str = Field(..., description="User-facing status or result message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Structured payload or output data")
    requires_confirmation: bool = Field(default=False, description="Whether action is pending user confirmation")
    confirmation_token: Optional[str] = Field(default=None, description="Token if pending confirmation")
    error: Optional[str] = Field(default=None, description="Error message if failed")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize tool result."""
        return self.model_dump()
