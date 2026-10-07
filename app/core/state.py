"""State management for myoneAI / Tamil JARVIS.

Tracks assistant execution states, registered services, and lightweight system telemetry.
"""

import threading
import time
from enum import Enum
from typing import Any, Dict, Optional
import psutil

from app.core.events import SystemEvent, event_bus


class AssistantState(str, Enum):
    """Lifecycle states of the personal assistant."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class ServiceStatus(str, Enum):
    """Operational status of individual modules."""
    STOPPED = "stopped"
    INITIALIZING = "initializing"
    RUNNING = "running"
    ERROR = "error"


class StateManager:
    """Thread-safe state and telemetry tracker."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: AssistantState = AssistantState.IDLE
        self._start_time: float = time.time()
        self._services: Dict[str, ServiceStatus] = {
            "voice": ServiceStatus.STOPPED,
            "wake_word": ServiceStatus.STOPPED,
            "ai": ServiceStatus.STOPPED,
            "monitoring": ServiceStatus.STOPPED,
            "security": ServiceStatus.STOPPED,
        }
        self._last_error: Optional[str] = None

    @property
    def current_state(self) -> AssistantState:
        """Get the current assistant state."""
        with self._lock:
            return self._state

    @property
    def uptime_seconds(self) -> float:
        """Return system uptime in seconds."""
        return time.time() - self._start_time

    def set_state(self, new_state: AssistantState, context: Optional[Dict[str, Any]] = None) -> None:
        """Transition to a new state and emit a state change event."""
        with self._lock:
            old_state = self._state
            if old_state == new_state:
                return
            self._state = new_state

        event_bus.emit(
            SystemEvent.STATE_CHANGED,
            {
                "old_state": old_state.value,
                "new_state": new_state.value,
                "context": context or {},
            },
        )

    def set_service_status(self, service_name: str, status: ServiceStatus) -> None:
        """Update the operational status of a registered service."""
        with self._lock:
            self._services[service_name] = status

    def get_service_status(self, service_name: str) -> ServiceStatus:
        """Retrieve the status of a specific service."""
        with self._lock:
            return self._services.get(service_name, ServiceStatus.STOPPED)

    def set_error(self, error_message: str) -> None:
        """Record an error and set state to ERROR."""
        with self._lock:
            self._last_error = error_message
        self.set_state(AssistantState.ERROR, {"error": error_message})
        event_bus.emit(SystemEvent.ERROR, {"error": error_message})

    def get_system_metrics(self) -> Dict[str, Any]:
        """Fetch lightweight, on-demand hardware telemetry (CPU, RAM, Battery)."""
        metrics: Dict[str, Any] = {
            "cpu_percent": 0.0,
            "ram_percent": 0.0,
            "ram_used_mb": 0.0,
            "ram_total_mb": 0.0,
            "battery_percent": None,
            "battery_plugged": None,
        }
        try:
            metrics["cpu_percent"] = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            metrics["ram_percent"] = mem.percent
            metrics["ram_used_mb"] = round((mem.total - mem.available) / (1024 * 1024), 1)
            metrics["ram_total_mb"] = round(mem.total / (1024 * 1024), 1)

            sensors_battery = getattr(psutil, "sensors_battery", None)
            if sensors_battery:
                battery = sensors_battery()
                if battery:
                    metrics["battery_percent"] = round(battery.percent, 1)
                    metrics["battery_plugged"] = battery.power_plugged
        except Exception:
            pass

        return metrics

    def get_snapshot(self) -> Dict[str, Any]:
        """Return a full snapshot of assistant health, status, and metrics."""
        with self._lock:
            services_copy = {k: v.value for k, v in self._services.items()}
            current_st = self._state.value
            last_err = self._last_error

        metrics = self.get_system_metrics()
        return {
            "state": current_st,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "services": services_copy,
            "last_error": last_err,
            "metrics": metrics,
        }


# Global state manager singleton
state_manager = StateManager()
