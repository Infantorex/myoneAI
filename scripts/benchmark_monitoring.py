"""System monitoring and telemetry performance benchmark for myoneAI.

Measures hardware metric extraction latency, threshold evaluation speed,
process enumeration overhead, and background duty cycle impact.
"""

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

from app.monitoring.alerts import AlertManager
from app.monitoring.battery import get_battery_metrics
from app.monitoring.cpu import get_cpu_metrics
from app.monitoring.disk import get_disk_metrics
from app.monitoring.manager import MonitoringManager
from app.monitoring.memory import get_memory_metrics
from app.monitoring.network import get_network_metrics
from app.monitoring.processes import get_process_metrics, get_top_processes
from app.monitoring.thresholds import ThresholdEngine


def run_benchmark():
    tracemalloc.start()
    process = psutil.Process(os.getpid())
    results = {}

    print("=" * 60)
    print("myoneAI — Monitoring Subsystem Performance Benchmark")
    print("=" * 60)

    # 1. CPU Metrics (Non-blocking sample_interval=None and 0.05s)
    t0 = time.perf_counter()
    cpu_nb = get_cpu_metrics(sample_interval=None)
    t_cpu_nb = (time.perf_counter() - t0) * 1000
    results["cpu_nonblocking_ms"] = round(t_cpu_nb, 3)
    print(f"[*] CPU Metrics (Instant):      {t_cpu_nb:7.3f} ms (Usage: {cpu_nb.usage_percent:.1f}%)")

    t0 = time.perf_counter()
    cpu_s = get_cpu_metrics(sample_interval=0.05)
    t_cpu_s = (time.perf_counter() - t0) * 1000
    results["cpu_sampled_ms"] = round(t_cpu_s, 3)
    print(f"[*] CPU Metrics (0.05s sample): {t_cpu_s:7.3f} ms (Usage: {cpu_s.usage_percent:.1f}%)")

    # 2. Memory Metrics
    t0 = time.perf_counter()
    for _ in range(50):
        mem = get_memory_metrics()
    t_mem_50 = (time.perf_counter() - t0) * 1000
    results["memory_metric_ms"] = round(t_mem_50 / 50, 3)
    print(f"[*] Memory Metrics:             {results['memory_metric_ms']:7.3f} ms (RAM: {mem.percent:.1f}%)")

    # 3. Disk Metrics
    t0 = time.perf_counter()
    for _ in range(50):
        disk = get_disk_metrics()
    t_disk_50 = (time.perf_counter() - t0) * 1000
    results["disk_metric_ms"] = round(t_disk_50 / 50, 3)
    print(f"[*] Disk Metrics:               {results['disk_metric_ms']:7.3f} ms (Disk: {disk.percent:.1f}%)")

    # 4. Battery Metrics
    t0 = time.perf_counter()
    for _ in range(50):
        bat = get_battery_metrics()
    t_bat_50 = (time.perf_counter() - t0) * 1000
    results["battery_metric_ms"] = round(t_bat_50 / 50, 3)
    bat_str = f"{bat.percent:.0f}%" if bat.percent is not None else "AC"
    print(f"[*] Battery Metrics:            {results['battery_metric_ms']:7.3f} ms (Battery: {bat_str})")

    # 5. Network Metrics
    t0 = time.perf_counter()
    for _ in range(50):
        net = get_network_metrics(check_latency=False)
    t_net_50 = (time.perf_counter() - t0) * 1000
    results["network_metric_ms"] = round(t_net_50 / 50, 3)
    print(f"[*] Network Metrics:            {results['network_metric_ms']:7.3f} ms (Available: {net.is_connected})")

    # 6. Process Metrics Collection
    t0 = time.perf_counter()
    procs = get_process_metrics(limit=5)
    t_procs = (time.perf_counter() - t0) * 1000
    results["process_metrics_ms"] = round(t_procs, 2)
    print(f"[*] Process Metrics (Top 5):    {t_procs:7.2f} ms ({procs.total_processes} processes scanned)")

    # 7. Complete Snapshot (Sync) without processes
    mgr = MonitoringManager()
    t0 = time.perf_counter()
    snap = mgr.get_snapshot_sync(include_processes=False, sample_interval=None)
    t_snap_fast = (time.perf_counter() - t0) * 1000
    results["snapshot_fast_ms"] = round(t_snap_fast, 3)
    print(f"[*] Full Snapshot (No Procs):   {t_snap_fast:7.3f} ms")

    # 8. Threshold Engine Evaluation (1000 evaluations)
    engine = ThresholdEngine()
    t0 = time.perf_counter()
    for _ in range(1000):
        _ = engine.evaluate(snap)
    t_engine_1000 = (time.perf_counter() - t0) * 1000
    results["threshold_eval_us"] = round((t_engine_1000 / 1000) * 1000, 3)
    print(f"[*] Threshold Engine Eval:      {results['threshold_eval_us']:7.3f} µs / evaluation")

    # 9. Alert Manager Dispatch (1000 checks)
    alert_mgr = AlertManager()
    t0 = time.perf_counter()
    for _ in range(1000):
        _ = alert_mgr.process_alerts([])
    t_alert_1000 = (time.perf_counter() - t0) * 1000
    results["alert_manager_us"] = round((t_alert_1000 / 1000) * 1000, 3)
    print(f"[*] Alert Manager Check:        {results['alert_manager_us']:7.3f} µs / check")

    # Resource Profile
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    mem_info = process.memory_info()

    results["rss_mb"] = round(mem_info.rss / (1024 * 1024), 2)
    results["traced_peak_kb"] = round(peak_mem / 1024, 2)
    print("-" * 60)
    print(f"[*] Monitoring Peak Heap:       {results['traced_peak_kb']:7.2f} KB")
    print(f"[*] Process RSS Memory:          {results['rss_mb']:7.2f} MB")
    print("=" * 60)

    return results


if __name__ == "__main__":
    res = run_benchmark()
    if "--json" in sys.argv:
        print(json.dumps(res, indent=2))
