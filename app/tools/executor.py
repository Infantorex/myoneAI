"""Secure tool execution engine for myoneAI (Phase 8).

Validates parameters, enforces permissions and confirmation flows, applies timeouts,
records security audits, and prevents arbitrary command execution.
"""

import asyncio
import inspect
import logging
import time
from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.core.events import ToolEvent, event_bus
from app.security.audit import audit_logger
from app.security.permissions import (
    PermissionLevel,
    PermissionManager,
    permission_manager,
)
from app.tools.registry import ToolRegistry, tool_registry
from app.tools.schemas import (
    ToolCall,
    ToolNotFoundError,
    ToolPermissionDeniedError,
    ToolResult,
    ToolTimeoutError,
    ToolValidationError,
)

logger = logging.getLogger("myoneAI.tools.executor")


class ToolExecutor:
    """Executes registered tools with strict parameter validation and security controls."""

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        permissions: Optional[PermissionManager] = None,
    ) -> None:
        self.registry = registry or tool_registry
        self.permissions = permissions or permission_manager
        self.settings = get_settings()

    async def execute(
        self,
        tool_call: ToolCall,
        confirmed: bool = False,
    ) -> ToolResult:
        """Execute a tool call with permission checks, timeout protection, and audit logging.

        Args:
            tool_call: ToolCall object with tool name and arguments.
            confirmed: Whether explicit confirmation was provided for CONFIRMATION_REQUIRED tools.

        Returns:
            Structured ToolResult.
        """
        start_time = time.time()
        tool_name = tool_call.tool.strip().lower()
        args = tool_call.arguments or {}

        event_bus.emit(ToolEvent.TOOL_REQUESTED, {"tool": tool_name, "arguments": args})

        # 1. Lookup in registry
        entry = self.registry.get(tool_name)
        if not entry:
            err_msg = f"Tool '{tool_name}' is not registered or allowed."
            audit_logger.log_tool_decision(tool_name, "UNKNOWN", "rejected", err_msg)
            event_bus.emit(ToolEvent.TOOL_FAILED, {"tool": tool_name, "error": err_msg})
            return ToolResult(
                success=False,
                tool=tool_name,
                message=f"Unknown tool '{tool_name}'.",
                error=err_msg,
            )

        schema, handler = entry

        # 2. Validate required parameters
        for required_key in schema.required_params:
            if required_key not in args or args[required_key] is None or str(args[required_key]).strip() == "":
                err_msg = f"Missing required parameter '{required_key}' for tool '{tool_name}'."
                audit_logger.log_tool_decision(tool_name, schema.permission.value, "validation_failed", err_msg)
                event_bus.emit(ToolEvent.TOOL_FAILED, {"tool": tool_name, "error": err_msg})
                return ToolResult(
                    success=False,
                    tool=tool_name,
                    message=f"Missing parameter '{required_key}'.",
                    error=err_msg,
                )

        # 3. Evaluate security permission
        perm_level, reason = self.permissions.evaluate_tool_permission(tool_name, args)

        if perm_level == PermissionLevel.BLOCKED:
            audit_logger.log_tool_decision(tool_name, perm_level.value, "blocked", reason)
            event_bus.emit(ToolEvent.TOOL_FAILED, {"tool": tool_name, "error": reason})
            return ToolResult(
                success=False,
                tool=tool_name,
                message=f"Action blocked by security policy: {reason}",
                error=reason,
            )

        # 4. Handle CONFIRMATION_REQUIRED actions
        if perm_level == PermissionLevel.CONFIRMATION_REQUIRED and not confirmed:
            prompt_msg = f"This action requires confirmation: {reason} Do you want to proceed?"
            pending = self.permissions.create_pending_confirmation(
                tool_name=tool_name,
                arguments=args,
                prompt_message=prompt_msg,
            )
            audit_logger.log_tool_decision(tool_name, perm_level.value, "pending_confirmation", f"Token: {pending.token}")
            event_bus.emit(ToolEvent.CONFIRMATION_REQUIRED, {"tool": tool_name, "token": pending.token})

            return ToolResult(
                success=False,
                tool=tool_name,
                message=f"{prompt_msg}\nஉறுதிப்படுத்துங்கள் (Say 'Yes' or 'Confirm' to proceed).",
                requires_confirmation=True,
                confirmation_token=pending.token,
            )

        # 5. Execute handler with timeout
        timeout = schema.timeout_sec or self.settings.tool_default_timeout
        try:
            if inspect.iscoroutinefunction(handler):
                result = await asyncio.wait_for(handler(**args), timeout=timeout)
            else:
                loop = asyncio.get_running_loop()
                result = await asyncio.wait_for(loop.run_in_executor(None, lambda: handler(**args)), timeout=timeout)

            elapsed = time.time() - start_time
            if isinstance(result, ToolResult):
                res = result
            else:
                res = ToolResult(
                    success=True,
                    tool=tool_name,
                    message=str(result),
                    data=result if isinstance(result, dict) else None,
                )

            audit_logger.log_tool_decision(tool_name, perm_level.value, "success" if res.success else "failed", res.message, duration_sec=elapsed)
            if res.success:
                event_bus.emit(ToolEvent.TOOL_EXECUTED, {"tool": tool_name, "result": res.message})
            else:
                event_bus.emit(ToolEvent.TOOL_FAILED, {"tool": tool_name, "error": res.error or res.message})

            return res

        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            err_msg = f"Tool '{tool_name}' execution timed out after {timeout:.1f}s."
            logger.error(err_msg)
            audit_logger.log_tool_decision(tool_name, perm_level.value, "timeout", err_msg, duration_sec=elapsed)
            event_bus.emit(ToolEvent.TOOL_FAILED, {"tool": tool_name, "error": err_msg})
            return ToolResult(
                success=False,
                tool=tool_name,
                message=f"Tool operation timed out ({tool_name}).",
                error=err_msg,
            )
        except Exception as exc:
            elapsed = time.time() - start_time
            logger.error("Error executing tool '%s': %s", tool_name, exc, exc_info=True)
            audit_logger.log_tool_decision(tool_name, perm_level.value, "error", str(exc), duration_sec=elapsed)
            event_bus.emit(ToolEvent.TOOL_FAILED, {"tool": tool_name, "error": str(exc)})
            return ToolResult(
                success=False,
                tool=tool_name,
                message=f"Error running {tool_name}: {exc}",
                error=str(exc),
            )


# Global tool executor singleton
tool_executor = ToolExecutor()
