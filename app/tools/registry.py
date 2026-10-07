"""Tool registry defining all explicit, allowlisted PC capabilities (Phase 8 & 9)."""

from typing import Any, Callable, Dict, List, Optional, Tuple

from app.security.permissions import PermissionLevel
from app.tools.applications import close_application, open_application
from app.tools.browser import open_website, search_web_browser
from app.tools.filesystem import delete_file, list_directory, open_directory, open_file
from app.tools.media import (
    media_next,
    media_play_pause,
    media_previous,
    set_volume,
    toggle_mute,
    volume_down,
    volume_up,
)
from app.tools.schemas import ToolSchema
from app.tools.screenshot import take_screenshot
from app.tools.system import (
    diagnose_system_performance,
    get_battery_status,
    get_cpu_status,
    get_cpu_usage,
    get_disk_status,
    get_disk_usage,
    get_memory_status,
    get_network_status,
    get_ram_usage,
    get_system_info,
    get_system_status,
    get_top_processes,
)


class ToolRegistry:
    """Central registry of registered tools and their executable handlers."""

    def __init__(self, register_defaults: bool = True) -> None:
        self._tools: Dict[str, Tuple[ToolSchema, Callable[..., Any]]] = {}
        if register_defaults:
            self._register_default_tools()

    def register(self, schema: ToolSchema, handler: Callable[..., Any], allow_override: bool = False) -> None:
        """Register a new allowlisted tool."""
        key = schema.name.lower().strip()
        if key in self._tools and not allow_override:
            raise ValueError(f"Tool '{schema.name}' is already registered.")
        self._tools[key] = (schema, handler)

    def get(self, name: str) -> Optional[Tuple[ToolSchema, Callable[..., Any]]]:
        """Fetch tool schema and handler by name."""
        return self._tools.get(name.lower().strip())

    def list_tools(self) -> List[ToolSchema]:
        """Return list of all registered tool schemas."""
        return [schema for schema, _ in self._tools.values()]

    def list_tool_names(self) -> List[str]:
        """Return list of registered tool names."""
        return list(self._tools.keys())

    def is_registered(self, name: str) -> bool:
        """Check if tool name is currently registered."""
        return name.lower().strip() in self._tools

    def get_tools_prompt_description(self) -> str:
        """Format registered tools as a concise prompt context for the AI."""
        lines = ["[Available PC Assistant Tools]:"]
        for schema in self.list_tools():
            lines.append(schema.to_prompt_desc())
        lines.append("[End Tools Description]")
        return "\n".join(lines)

    def _register_default_tools(self) -> None:
        """Register all default safe and confirmed PC assistant tools."""
        # 1. Application Tools
        self.register(
            ToolSchema(
                name="open_application",
                description="Launch an approved application (e.g. chrome, edge, vscode, notepad, calculator, explorer)",
                parameters={"application": {"type": "string", "description": "Name or alias of application"}},
                required_params=["application"],
                permission=PermissionLevel.SAFE,
            ),
            open_application,
        )
        self.register(
            ToolSchema(
                name="close_application",
                description="Terminate running processes for an approved application",
                parameters={"application": {"type": "string", "description": "Name or alias of application"}},
                required_params=["application"],
                permission=PermissionLevel.CONFIRMATION_REQUIRED,
            ),
            close_application,
        )

        # 2. Browser Tools
        self.register(
            ToolSchema(
                name="open_website",
                description="Open a web page URL in the browser (HTTP/HTTPS only)",
                parameters={"url": {"type": "string", "description": "Web address to open"}},
                required_params=["url"],
                permission=PermissionLevel.SAFE,
            ),
            open_website,
        )
        self.register(
            ToolSchema(
                name="search_web_browser",
                description="Search Google query in default browser",
                parameters={"query": {"type": "string", "description": "Search query keywords"}},
                required_params=["query"],
                permission=PermissionLevel.SAFE,
            ),
            search_web_browser,
        )

        # 3. Filesystem Tools
        self.register(
            ToolSchema(
                name="list_directory",
                description="List contents of an approved workspace directory",
                parameters={"directory": {"type": "string", "description": "Folder path (optional)"}},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            list_directory,
        )
        self.register(
            ToolSchema(
                name="open_directory",
                description="Open an approved folder in File Explorer",
                parameters={"directory": {"type": "string", "description": "Folder path (optional)"}},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            open_directory,
        )
        self.register(
            ToolSchema(
                name="open_file",
                description="Open a file using default system viewer",
                parameters={"file_path": {"type": "string", "description": "File path"}},
                required_params=["file_path"],
                permission=PermissionLevel.SAFE,
            ),
            open_file,
        )
        self.register(
            ToolSchema(
                name="delete_file",
                description="Permanently delete a file within user workspace (requires confirmation)",
                parameters={"file_path": {"type": "string", "description": "File path to delete"}},
                required_params=["file_path"],
                permission=PermissionLevel.CONFIRMATION_REQUIRED,
            ),
            delete_file,
        )

        # 4. Media & Volume Controls
        self.register(
            ToolSchema(
                name="volume_up",
                description="Increase audio volume",
                parameters={"step_percent": {"type": "integer", "description": "Volume increase percentage (default 10)"}},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            volume_up,
        )
        self.register(
            ToolSchema(
                name="volume_down",
                description="Decrease audio volume",
                parameters={"step_percent": {"type": "integer", "description": "Volume decrease percentage (default 10)"}},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            volume_down,
        )
        self.register(
            ToolSchema(
                name="set_volume",
                description="Set specific volume percentage (0-100)",
                parameters={"volume_percent": {"type": "integer", "description": "Target volume percentage"}},
                required_params=["volume_percent"],
                permission=PermissionLevel.SAFE,
            ),
            set_volume,
        )
        self.register(
            ToolSchema(
                name="toggle_mute",
                description="Toggle system mute on or off",
                parameters={},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            toggle_mute,
        )
        self.register(
            ToolSchema(
                name="media_play_pause",
                description="Toggle Play / Pause for active media",
                parameters={},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            media_play_pause,
        )
        self.register(
            ToolSchema(
                name="media_next",
                description="Skip to next media track",
                parameters={},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            media_next,
        )
        self.register(
            ToolSchema(
                name="media_previous",
                description="Return to previous media track",
                parameters={},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            media_previous,
        )

        # 5. Screenshot
        self.register(
            ToolSchema(
                name="take_screenshot",
                description="Capture full screen snapshot and save locally",
                parameters={},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            take_screenshot,
        )

        # 6. System Monitoring & Telemetry (Phase 8 & 9)
        self.register(
            ToolSchema(
                name="get_system_status",
                description="Retrieve full system health overview (CPU, RAM, Disk, Battery, Network)",
                parameters={},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            get_system_status,
        )
        self.register(
            ToolSchema(
                name="get_system_info",
                description="Retrieve overview of OS, CPU, RAM, and battery",
                parameters={},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            get_system_info,
        )
        self.register(
            ToolSchema(
                name="get_cpu_status",
                description="Read active CPU utilization percentage and core count",
                parameters={},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            get_cpu_status,
        )
        self.register(
            ToolSchema(
                name="get_cpu_usage",
                description="Read active CPU load percentage",
                parameters={},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            get_cpu_usage,
        )
        self.register(
            ToolSchema(
                name="get_memory_status",
                description="Read RAM memory utilization, used MB, and free capacity",
                parameters={},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            get_memory_status,
        )
        self.register(
            ToolSchema(
                name="get_ram_usage",
                description="Read memory utilization and free RAM",
                parameters={},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            get_ram_usage,
        )
        self.register(
            ToolSchema(
                name="get_disk_status",
                description="Read storage disk usage percentage and free gigabytes",
                parameters={"path": {"type": "string", "description": "Optional drive or path"}},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            get_disk_status,
        )
        self.register(
            ToolSchema(
                name="get_disk_usage",
                description="Read disk storage usage and free space",
                parameters={},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            get_disk_usage,
        )
        self.register(
            ToolSchema(
                name="get_battery_status",
                description="Read battery percentage, AC adapter status, and charging state",
                parameters={},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            get_battery_status,
        )
        self.register(
            ToolSchema(
                name="get_network_status",
                description="Check internet connectivity and local network configuration",
                parameters={"check_latency": {"type": "boolean", "description": "Optional active latency ping"}},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            get_network_status,
        )
        self.register(
            ToolSchema(
                name="get_top_processes",
                description="Identify applications consuming the most RAM or CPU resources",
                parameters={
                    "limit": {"type": "integer", "description": "Number of processes to return (default 5)"},
                    "sort_by": {"type": "string", "description": "Sort metric: 'memory' or 'cpu'"},
                },
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            get_top_processes,
        )
        self.register(
            ToolSchema(
                name="diagnose_system_performance",
                description="Analyze system bottlenecks (RAM, CPU, Disk, Battery) and provide actionable suggestions for slowness",
                parameters={},
                required_params=[],
                permission=PermissionLevel.SAFE,
            ),
            diagnose_system_performance,
        )


# Global tool registry singleton
tool_registry = ToolRegistry()


def register_tool(
    name: str,
    handler: Callable[..., Any],
    description: str = "",
    parameters: Optional[Dict[str, Any]] = None,
    required_params: Optional[List[str]] = None,
    permission: PermissionLevel = PermissionLevel.SAFE,
    timeout_sec: float = 10.0,
) -> None:
    """Convenience helper to register an allowlisted tool with the global registry."""
    schema = ToolSchema(
        name=name,
        description=description,
        parameters=parameters or {},
        required_params=required_params or [],
        permission=permission,
        timeout_sec=timeout_sec,
    )
    tool_registry.register(schema, handler)
