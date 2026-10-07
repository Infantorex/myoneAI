"""System telemetry and hardware monitoring tools for myoneAI (Phase 8 & 9).

Safe, read-only diagnostic metrics using psutil, platform, and app.monitoring subsystems.
"""

import asyncio
import logging
import platform
from typing import Any, Dict, Optional

from app.monitoring.battery import get_battery_metrics
from app.monitoring.cpu import get_cpu_metrics
from app.monitoring.disk import get_disk_metrics
from app.monitoring.manager import monitoring_manager
from app.monitoring.memory import get_memory_metrics
from app.monitoring.network import get_network_metrics
from app.monitoring.processes import get_process_metrics, get_top_processes as fetch_top_processes
from app.tools.schemas import ToolResult

logger = logging.getLogger("myoneAI.tools.system")


def get_system_status() -> ToolResult:
    """Retrieve full health status across CPU, RAM, Disk, Battery, and Network."""
    try:
        snapshot = monitoring_manager.get_snapshot_sync(include_processes=False)
        summary = snapshot.to_summary()

        # Build natural Tamil response
        tamil_parts = []
        if snapshot.cpu:
            tamil_parts.append(f"CPU பயன்பாடு {snapshot.cpu.usage_percent:.0f}%")
        if snapshot.memory:
            tamil_parts.append(f"RAM {snapshot.memory.percent:.0f}%")
        if snapshot.disk:
            tamil_parts.append(f"வட்டு பயன்பாடு {snapshot.disk.percent:.0f}%")
        if snapshot.battery and snapshot.battery.is_available:
            state = "சார்ஜிங்" if snapshot.battery.power_plugged else "பேட்டரி"
            tamil_parts.append(f"பேட்டரி {snapshot.battery.percent:.0f}% ({state})")

        tamil_msg = "லேப்டாப் நிலை: " + ", ".join(tamil_parts) + "."

        return ToolResult(
            success=True,
            tool="get_system_status",
            message=f"{summary}. {tamil_msg}",
            data=snapshot.to_dict(),
        )
    except Exception as exc:
        logger.error("Failed to read system status: %s", exc)
        return ToolResult(
            success=False,
            tool="get_system_status",
            message=f"Error reading system status: {exc}",
            error=str(exc),
        )


def get_system_info() -> ToolResult:
    """Retrieve general hardware, OS, and runtime specifications."""
    res = get_system_status()
    os_str = f"{platform.system()} {platform.release()} ({platform.machine()})"
    res.tool = "get_system_info"
    res.message = f"OS: {os_str} | {res.message}"
    if isinstance(res.data, dict):
        res.data["os"] = os_str
    return res


def get_battery_status() -> ToolResult:
    """Fetch current battery charge percentage and power connection state."""
    try:
        batt = get_battery_metrics()
        if not batt.is_available:
            return ToolResult(
                success=True,
                tool="get_battery_status",
                message="Battery information isn't available on this device (Desktop/AC). சாதனத்தில் பேட்டரி இல்லை.",
                data=batt.to_dict(),
            )

        charge_state = "charging" if batt.power_plugged else "on battery power"
        tamil_state = "சார்ஜிங் ஆகிறது" if batt.power_plugged else "பேட்டரியில் இயங்குகிறது"
        msg = f"Battery is at {batt.percent:.0f}% and {charge_state}. பேட்டரி {batt.percent:.0f}% உள்ளது ({tamil_state})."

        return ToolResult(
            success=True,
            tool="get_battery_status",
            message=msg,
            data=batt.to_dict(),
        )
    except Exception as exc:
        logger.error("Failed to query battery status: %s", exc)
        return ToolResult(
            success=False,
            tool="get_battery_status",
            message=f"Error querying battery: {exc}",
            error=str(exc),
        )


def get_cpu_status() -> ToolResult:
    """Read active CPU load percentage and core information."""
    try:
        cpu = get_cpu_metrics(sample_interval=0.1)
        msg = f"CPU usage is around {cpu.usage_percent:.1f}% ({cpu.logical_cores} cores). CPU பயன்பாடு {cpu.usage_percent:.1f}% ஆக உள்ளது."
        return ToolResult(
            success=True,
            tool="get_cpu_status",
            message=msg,
            data=cpu.to_dict(),
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="get_cpu_status",
            message=f"Failed to read CPU usage: {exc}",
            error=str(exc),
        )


def get_cpu_usage() -> ToolResult:
    """Alias for get_cpu_status returning tool='get_cpu_usage'."""
    res = get_cpu_status()
    res.tool = "get_cpu_usage"
    return res


def get_memory_status() -> ToolResult:
    """Read memory utilization and free capacity."""
    try:
        mem = get_memory_metrics()
        used_gb = mem.used_mb / 1024
        total_gb = mem.total_mb / 1024
        msg = (
            f"You're using around {mem.percent:.0f}% of your RAM ({used_gb:.1f}GB / {total_gb:.1f}GB). "
            f"RAM பயன்பாடு {mem.percent:.0f}% ஆக உள்ளது."
        )
        return ToolResult(
            success=True,
            tool="get_memory_status",
            message=msg,
            data=mem.to_dict(),
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="get_memory_status",
            message=f"Failed to read memory usage: {exc}",
            error=str(exc),
        )


def get_ram_usage() -> ToolResult:
    """Alias for get_memory_status returning tool='get_ram_usage'."""
    res = get_memory_status()
    res.tool = "get_ram_usage"
    return res


def get_disk_status(path: Optional[str] = None) -> ToolResult:
    """Read storage disk capacity and available space."""
    try:
        disk = get_disk_metrics(path=path)
        msg = (
            f"Disk storage is {disk.percent:.0f}% used with {disk.free_gb:.1f}GB free out of {disk.total_gb:.1f}GB. "
            f"வட்டு சேமிப்பகம் {disk.percent:.0f}% பயன்பாட்டில் உள்ளது (மீதம்: {disk.free_gb:.1f}GB)."
        )
        return ToolResult(
            success=True,
            tool="get_disk_status",
            message=msg,
            data=disk.to_dict(),
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="get_disk_status",
            message=f"Failed to read disk status: {exc}",
            error=str(exc),
        )


def get_disk_usage() -> ToolResult:
    """Alias for get_disk_status returning tool='get_disk_usage'."""
    res = get_disk_status()
    res.tool = "get_disk_usage"
    return res


def get_network_status(check_latency: bool = False) -> ToolResult:
    """Read network connection availability and IP address."""
    try:
        net = get_network_metrics(check_latency=check_latency)
        if net.is_connected:
            latency_str = f" (Latency: {net.latency_ms:.0f}ms)" if net.latency_ms is not None else ""
            msg = f"Network is connected (IP: {net.ip_address}){latency_str}. இணைய இணைப்பு செயலில் உள்ளது."
        else:
            msg = "Network is disconnected. No active internet connection. இணைய இணைப்பு துண்டிக்கப்பட்டுள்ளது."

        return ToolResult(
            success=True,
            tool="get_network_status",
            message=msg,
            data=net.to_dict(),
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="get_network_status",
            message=f"Failed to read network status: {exc}",
            error=str(exc),
        )


def get_top_processes(limit: int = 5, sort_by: str = "memory") -> ToolResult:
    """Identify top resource-consuming applications."""
    try:
        procs = fetch_top_processes(limit=limit, sort_by=sort_by)
        if not procs:
            return ToolResult(
                success=True,
                tool="get_top_processes",
                message="No active process telemetry available.",
                data={"processes": []},
            )

        top_one = procs[0]
        if sort_by.lower() == "cpu":
            lead_msg = f"{top_one.name} is currently using the most CPU ({top_one.cpu_percent:.1f}%)."
            tamil_lead = f"{top_one.name} அதிக CPU பயன்பாட்டை ({top_one.cpu_percent:.1f}%) கொண்டுள்ளது."
        else:
            lead_msg = f"{top_one.name} is currently using the most memory ({top_one.memory_mb:.0f}MB, {top_one.memory_percent:.1f}%)."
            tamil_lead = f"{top_one.name} அதிக நினைவகத்தை ({top_one.memory_mb:.0f}MB) பயன்படுத்துகிறது."

        proc_list_str = ", ".join([f"{p.name} ({p.memory_mb:.0f}MB)" for p in procs])
        full_msg = f"{lead_msg} {tamil_lead} [Top: {proc_list_str}]"

        return ToolResult(
            success=True,
            tool="get_top_processes",
            message=full_msg,
            data={"processes": [p.to_dict() for p in procs], "sort_by": sort_by},
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            tool="get_top_processes",
            message=f"Failed to query top processes: {exc}",
            error=str(exc),
        )


def diagnose_system_performance() -> ToolResult:
    """Diagnose bottlenecks (RAM, CPU, Disk, Battery throttling) and provide suggestions."""
    try:
        try:
            loop = asyncio.get_running_loop()
            diag = loop.run_until_complete(monitoring_manager.diagnose_slow_system()) if not loop.is_running() else None
        except RuntimeError:
            diag = asyncio.run(monitoring_manager.diagnose_slow_system())

        if diag is None:
            diag = asyncio.run(monitoring_manager.diagnose_slow_system())

        summary = diag.get("diagnosis_summary", "System running normally.")
        tamil_sum = diag.get("tamil_summary", "")
        recs = " ".join(diag.get("recommendations", []))
        tamil_recs = " ".join(diag.get("tamil_recommendations", []))

        full_msg = f"{summary} {tamil_sum}\nRecommendation: {recs} {tamil_recs}"

        return ToolResult(
            success=True,
            tool="diagnose_system_performance",
            message=full_msg,
            data=diag,
        )
    except Exception as exc:
        logger.error("Failed to diagnose system performance: %s", exc)
        return ToolResult(
            success=False,
            tool="diagnose_system_performance",
            message=f"Failed to diagnose performance: {exc}",
            error=str(exc),
        )
