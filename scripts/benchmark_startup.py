"""Startup and initialization performance benchmark for myoneAI.

Measures cold import times, component initialization latencies, process memory, and thread counts.
"""

import gc
import json
import os
import sys
import time
import tracemalloc
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import psutil


def run_benchmark():
    tracemalloc.start()
    process = psutil.Process(os.getpid())
    results = {}

    print("=" * 60)
    print("myoneAI — Startup & Initialization Benchmark")
    print("=" * 60)

    # 1. Config Loading
    t0 = time.perf_counter()
    from app.core.config import get_settings
    settings = get_settings()
    t_config = (time.perf_counter() - t0) * 1000
    results["config_init_ms"] = round(t_config, 2)
    print(f"[*] Configuration Init:         {t_config:7.2f} ms")

    # 2. Core State & Events
    t0 = time.perf_counter()
    from app.core.events import event_bus
    from app.core.state import state_manager
    t_core = (time.perf_counter() - t0) * 1000
    results["core_state_events_ms"] = round(t_core, 2)
    print(f"[*] Core State & Events Init:    {t_core:7.2f} ms")

    # 3. Security & Permissions
    t0 = time.perf_counter()
    from app.security.permissions import permission_manager
    from app.security.audit import audit_logger
    t_sec = (time.perf_counter() - t0) * 1000
    results["security_permissions_ms"] = round(t_sec, 2)
    print(f"[*] Security & Permissions Init: {t_sec:7.2f} ms")

    # 4. Memory Manager & Store
    t0 = time.perf_counter()
    from app.core.memory.manager import memory_manager
    t_mem = (time.perf_counter() - t0) * 1000
    results["memory_manager_ms"] = round(t_mem, 2)
    print(f"[*] Memory Subsystem Init:       {t_mem:7.2f} ms")

    # 5. Productivity Manager & Database
    t0 = time.perf_counter()
    from app.productivity.manager import productivity_manager
    t_prod = (time.perf_counter() - t0) * 1000
    results["productivity_manager_ms"] = round(t_prod, 2)
    print(f"[*] Productivity Subsystem Init: {t_prod:7.2f} ms")

    # 6. Tools & Registry
    t0 = time.perf_counter()
    from app.tools.registry import ToolRegistry
    from app.tools.executor import tool_executor
    tool_reg = ToolRegistry()
    t_tools = (time.perf_counter() - t0) * 1000
    results["tools_registry_ms"] = round(t_tools, 2)
    print(f"[*] Tools Registry Init:         {t_tools:7.2f} ms")

    # 7. AI Conversation Engine
    t0 = time.perf_counter()
    from app.ai.manager import conversation_manager
    t_ai = (time.perf_counter() - t0) * 1000
    results["ai_engine_ms"] = round(t_ai, 2)
    print(f"[*] AI Conversation Manager Init:{t_ai:7.2f} ms")

    # 8. Monitoring Manager
    t0 = time.perf_counter()
    from app.monitoring.manager import monitoring_manager
    t_mon = (time.perf_counter() - t0) * 1000
    results["monitoring_manager_ms"] = round(t_mon, 2)
    print(f"[*] Monitoring Manager Init:     {t_mon:7.2f} ms")

    # 9. Voice Subsystems (VAD, AudioPlayer, STT/TTS factories)
    t0 = time.perf_counter()
    from app.voice.audio import audio_player
    from app.voice.vad import VoiceActivityDetector
    from app.voice.tts import get_tts_provider
    from app.voice.stt import get_stt_provider
    t_voice = (time.perf_counter() - t0) * 1000
    results["voice_subsystems_ms"] = round(t_voice, 2)
    print(f"[*] Voice Subsystems Init:       {t_voice:7.2f} ms")

    # 10. Cloud Client & Transport
    t0 = time.perf_counter()
    from app.cloud.client import cloud_client
    t_cloud = (time.perf_counter() - t0) * 1000
    results["cloud_client_ms"] = round(t_cloud, 2)
    print(f"[*] Cloud Client Init:           {t_cloud:7.2f} ms")

    # 11. Web FastAPI App & Routes
    t0 = time.perf_counter()
    from web.api.server import create_app
    app = create_app()
    t_web = (time.perf_counter() - t0) * 1000
    results["fastapi_app_ms"] = round(t_web, 2)
    print(f"[*] FastAPI Application Init:    {t_web:7.2f} ms")

    # Total Sum
    total_startup_ms = sum(results.values())
    results["total_startup_ms"] = round(total_startup_ms, 2)
    print("-" * 60)
    print(f"[*] Total Subsystem Init Time:   {total_startup_ms:7.2f} ms")

    # Resource Profile
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    mem_info = process.memory_info()

    results["rss_mb"] = round(mem_info.rss / (1024 * 1024), 2)
    results["vms_mb"] = round(mem_info.vms / (1024 * 1024), 2)
    results["traced_peak_mb"] = round(peak_mem / (1024 * 1024), 2)
    results["threads_count"] = process.num_threads()

    print(f"[*] Process RSS Memory:          {results['rss_mb']:7.2f} MB")
    print(f"[*] Traced Python Peak Heap:     {results['traced_peak_mb']:7.2f} MB")
    print(f"[*] Active Process Threads:      {results['threads_count']:7d}")
    print("=" * 60)

    return results


if __name__ == "__main__":
    res = run_benchmark()
    if "--json" in sys.argv:
        print(json.dumps(res, indent=2))
