"""System telemetry routes for myoneAI Web Dashboard (Phase 11).

Provides on-demand system status, diagnostics, and process information reusing Phase 9 monitoring.
"""

import logging
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query

from app.monitoring.manager import MonitoringManager, monitoring_manager
from app.monitoring.models import MonitoringSnapshot
from app.monitoring.processes import get_process_metrics
from web.api.auth import require_auth
from web.api.schemas import (
    SystemDiagnosisResponse,
    SystemStatusResponse,
    TopProcessItem,
)

logger = logging.getLogger("myoneAI.web.routes.system")

router = APIRouter(prefix="/system", tags=["System Telemetry"])


@router.get("/status", response_model=SystemStatusResponse, dependencies=[Depends(require_auth)])
async def get_system_status() -> SystemStatusResponse:
    """Retrieve instantaneous hardware telemetry (CPU, RAM, Disk, Battery, Network)."""
    snapshot: MonitoringSnapshot = await monitoring_manager.get_snapshot(
        include_processes=False,
        sample_interval=0.05,
    )

    battery_pct = snapshot.battery.percent if snapshot.battery and snapshot.battery.is_available else None
    battery_plugged = snapshot.battery.power_plugged if snapshot.battery and snapshot.battery.is_available else None

    return SystemStatusResponse(
        cpu_percent=round(snapshot.cpu.usage_percent, 1),
        memory_percent=round(snapshot.memory.percent, 1),
        disk_percent=round(snapshot.disk.percent, 1),
        battery_percent=round(battery_pct, 1) if battery_pct is not None else None,
        battery_plugged=battery_plugged,
        network_available=bool(snapshot.network and snapshot.network.is_connected),
    )


@router.get("/diagnosis", response_model=SystemDiagnosisResponse, dependencies=[Depends(require_auth)])
async def get_system_diagnosis() -> SystemDiagnosisResponse:
    """Retrieve system diagnostics with top consuming processes and warnings."""
    snapshot: MonitoringSnapshot = await monitoring_manager.get_snapshot(
        include_processes=True,
        process_limit=5,
        sample_interval=0.1,
    )

    warnings: List[str] = []
    if snapshot.cpu.usage_percent > 85:
        warnings.append(f"High CPU utilization: {snapshot.cpu.usage_percent:.1f}%")
    if snapshot.memory.percent > 90:
        warnings.append(f"High RAM utilization: {snapshot.memory.percent:.1f}%")
    if snapshot.disk.percent > 90:
        warnings.append(f"Low disk storage remaining: {snapshot.disk.percent:.1f}% used")
    if snapshot.battery and snapshot.battery.is_available and snapshot.battery.percent <= 20 and not snapshot.battery.power_plugged:
        warnings.append(f"Battery low: {snapshot.battery.percent:.0f}% remaining, connect charger")

    top_cpu = []
    top_mem = []
    if snapshot.processes:
        for p in snapshot.processes.top_cpu[:5]:
            top_cpu.append(TopProcessItem(
                pid=p.pid,
                name=p.name,
                cpu_percent=round(p.cpu_percent, 1),
                memory_percent=round(p.memory_percent, 1),
                memory_mb=round(p.memory_mb, 1),
            ))
        for p in snapshot.processes.top_memory[:5]:
            top_mem.append(TopProcessItem(
                pid=p.pid,
                name=p.name,
                cpu_percent=round(p.cpu_percent, 1),
                memory_percent=round(p.memory_percent, 1),
                memory_mb=round(p.memory_mb, 1),
            ))

    status_str = "healthy" if not warnings else ("warning" if len(warnings) <= 2 else "critical")

    return SystemDiagnosisResponse(
        status=status_str,
        warnings=warnings,
        top_cpu_processes=top_cpu,
        top_memory_processes=top_mem,
    )


@router.get("/processes", dependencies=[Depends(require_auth)])
async def get_system_processes(limit: int = Query(default=10, ge=1, le=50)) -> Dict[str, Any]:
    """Retrieve top CPU and Memory processes."""
    procs = get_process_metrics(limit=limit)
    return {
        "success": True,
        "processes": procs.to_dict(),
    }
