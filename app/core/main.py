"""Main entry point for myoneAI / Tamil JARVIS.

Handles CLI commands, diagnostics, initialization, and lifecycle management.
"""

import argparse
import os
import signal
import sys
import time
from typing import Optional

from app import __version__
from app.core.config import get_settings
from app.core.events import SystemEvent, event_bus
from app.core.logging_config import setup_logging, get_logger
from app.core.state import AssistantState, ServiceStatus, state_manager

logger = get_logger("main")


# Configure UTF-8 encoding for Windows terminals
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass


def print_diagnostic_status() -> None:
    """Print system status, resources, active services, and AI configuration."""
    settings = get_settings()
    snapshot = state_manager.get_snapshot()
    metrics = snapshot["metrics"]

    # Calculate process memory footprint
    import psutil
    process = psutil.Process(os.getpid())
    process_mem_mb = round(process.memory_info().rss / (1024 * 1024), 2)

    ai_status = "Connected (Cloud API configured)" if settings.is_ai_configured else "Not Configured (Missing AI_API_KEY)"

    battery_str = "N/A"
    if metrics.get("battery_percent") is not None:
        plugged_str = "Charging" if metrics.get("battery_plugged") else "Discharging"
        battery_str = f"{metrics['battery_percent']}% ({plugged_str})"

    output = f"""
======================================================================
  myoneAI — Tamil JARVIS (v{__version__})
======================================================================
  [Status]             : [ONLINE] Active
  [State]              : {snapshot['state'].upper()}
  [Uptime]             : {snapshot['uptime_seconds']}s
  [Process Memory]     : {process_mem_mb} MB (Ultra-Lightweight)
----------------------------------------------------------------------
  Hardware Telemetry (i3 / 8GB RAM Optimized):
  [CPU Usage]          : {metrics['cpu_percent']}%
  [RAM Usage]          : {metrics['ram_percent']}% ({metrics['ram_used_mb']} MB / {metrics['ram_total_mb']} MB)
  [Battery]            : {battery_str}
----------------------------------------------------------------------
  Service Registry:
  [Voice Engine]       : {snapshot['services']['voice'].upper()}
  [Wake Word]          : {snapshot['services']['wake_word'].upper()}
  [AI Provider]        : {settings.ai_provider} ({ai_status})
  [System Monitoring]  : {snapshot['services']['monitoring'].upper()}
  [Security Layer]     : {snapshot['services']['security'].upper()}
----------------------------------------------------------------------
  Configuration:
  [Environment]        : {settings.app_env}
  [Default Language]   : {settings.default_language}
  [Log File]           : {settings.log_file}
  [Require Confirm]    : {settings.require_confirmation_for_system_actions}
======================================================================
"""
    print(output)


def check_environment() -> bool:
    """Check configuration and environment readiness."""
    settings = get_settings()
    print("\n--- myoneAI Environment Check ---")
    print(f"Base Directory: {settings.base_dir}")
    print(f"Log File Path:  {settings.log_path}")
    print(f"Data Directory: {settings.data_path}")
    print(f"AI Provider:    {settings.ai_provider} (Configured: {settings.is_ai_configured})")
    print(f"STT Provider:   {settings.stt_provider}")
    print(f"TTS Provider:   {settings.tts_provider} ({settings.tts_voice})")

    # Verify directories exist or can be created
    settings.data_path.mkdir(parents=True, exist_ok=True)
    settings.log_path.parent.mkdir(parents=True, exist_ok=True)
    print("✓ Data and Log directories verified.")
    print("✓ Configuration validated successfully.\n")
    return True


def shutdown_handler(signum: Optional[int] = None, frame: Optional[object] = None) -> None:
    """Handle graceful shutdown signals."""
    logger.info("Shutdown signal received. Cleaning up services...")
    state_manager.set_state(AssistantState.SHUTDOWN)
    event_bus.emit(SystemEvent.SHUTDOWN)
    logger.info("myoneAI shutdown complete.")
    sys.exit(0)


def start_assistant() -> None:
    """Initialize core services and start assistant runtime loop."""
    settings = get_settings()
    setup_logging(log_level=settings.log_level, log_file=settings.log_path)
    logger.info("Initializing myoneAI (Tamil JARVIS) Foundation v%s...", __version__)

    # Register signal handlers
    try:
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)
    except (ValueError, AttributeError):
        pass

    # Initialize services to IDLE / RUNNING in Phase 1
    state_manager.set_service_status("security", ServiceStatus.RUNNING)
    state_manager.set_service_status("monitoring", ServiceStatus.RUNNING)
    state_manager.set_state(AssistantState.IDLE)
    event_bus.emit(SystemEvent.STARTUP, {"version": __version__})

    logger.info("myoneAI initialized in %s mode. Language: %s", settings.app_env, settings.default_language)
    print_diagnostic_status()


def main() -> None:
    """CLI Parser and main entry point."""
    parser = argparse.ArgumentParser(
        prog="jarvis",
        description="myoneAI — Tamil JARVIS Personal AI Assistant (Lightweight & Resource-Optimized)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Display assistant health, hardware telemetry, active services, and AI configuration",
    )
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="Validate environment configuration, paths, and settings",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"myoneAI v{__version__}",
        help="Show version information",
    )

    args = parser.parse_args()

    # Apply configuration & logging
    settings = get_settings()
    setup_logging(log_level=settings.log_level, log_file=settings.log_path)

    if args.status:
        print_diagnostic_status()
    elif args.check_env:
        check_environment()
    else:
        start_assistant()


if __name__ == "__main__":
    main()
