"""Cloud communication and protocol performance benchmark for myoneAI.

Measures HMAC-SHA256 signature computation, replay protection throughput,
offline queue operations, and heartbeat serialization overhead.
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

from app.cloud.authentication import compute_signature, sign_message, verify_message_signature
from app.cloud.heartbeat import HeartbeatManager
from app.cloud.protocol import CloudMessage, MessageType, ReplayProtection
from app.cloud.queue import OfflineEventQueue


def run_benchmark():
    tracemalloc.start()
    process = psutil.Process(os.getpid())
    results = {}

    print("=" * 60)
    print("myoneAI — Cloud Protocol Performance Benchmark")
    print("=" * 60)

    secret = "perf_test_secret_token_1234567890abcdef"
    device_id = "jarvis_perf_device_id_001"

    # 1. HMAC-SHA256 Signature Computation (5000 iterations)
    payload = {"status": "online", "cpu": 12.5, "memory": 45.2, "battery": 88}
    msg = CloudMessage(
        type=MessageType.HEARTBEAT,
        device_id=device_id,
        payload=payload,
    )
    t0 = time.perf_counter()
    for _ in range(5000):
        _ = compute_signature(secret, msg)
    t_hmac_5000 = (time.perf_counter() - t0) * 1000
    us_per_sig = (t_hmac_5000 / 5000) * 1000
    results["hmac_sign_us"] = round(us_per_sig, 3)
    results["hmac_throughput_ops_sec"] = round(5000 / (t_hmac_5000 / 1000), 1)
    print(f"[*] HMAC-SHA256 Sign:           {us_per_sig:7.3f} µs / sign ({results['hmac_throughput_ops_sec']:.0f} ops/sec)")

    # 2. Message Signing & Verification Roundtrip (5000 iterations)
    t0 = time.perf_counter()
    for _ in range(5000):
        signed = sign_message(secret, msg)
        valid = verify_message_signature(secret, signed)
    t_roundtrip_5000 = (time.perf_counter() - t0) * 1000
    us_per_roundtrip = (t_roundtrip_5000 / 5000) * 1000
    results["sign_and_verify_us"] = round(us_per_roundtrip, 3)
    print(f"[*] Message Sign & Verify:      {us_per_roundtrip:7.3f} µs / roundtrip")

    # 3. Replay Protection Throughput (10,000 unique checks)
    replay = ReplayProtection(max_drift_seconds=300.0)
    now = time.time()
    t0 = time.perf_counter()
    for i in range(10000):
        test_msg = CloudMessage(
            id=f"req_{i}",
            type=MessageType.HEARTBEAT,
            timestamp=now,
            device_id=device_id,
            payload={},
        )
        replay.validate_message(test_msg, current_time=now)
    t_replay_10000 = (time.perf_counter() - t0) * 1000
    us_per_replay = (t_replay_10000 / 10000) * 1000
    results["replay_validation_us"] = round(us_per_replay, 3)
    print(f"[*] Replay Filter Validate:     {us_per_replay:7.3f} µs / validation")

    # 4. Offline Event Queue Throughput (1000 enqueues & bounds enforcement)
    q = OfflineEventQueue(max_size=100)
    t0 = time.perf_counter()
    for i in range(1000):
        q.enqueue(CloudMessage(
            type=MessageType.STATUS.value,
            device_id=device_id,
            payload={"metric": i, "val": i * 2},
        ))
    t_queue_1000 = (time.perf_counter() - t0) * 1000
    us_per_q = (t_queue_1000 / 1000) * 1000
    results["queue_enqueue_us"] = round(us_per_q, 3)
    print(f"[*] Offline Queue Enqueue:      {us_per_q:7.3f} µs / enqueue (Bounded size: {q.size})")

    # 5. Heartbeat Snapshot Assembly
    hb_mgr = HeartbeatManager()
    import asyncio
    async def bench_hb():
        t0 = time.perf_counter()
        for _ in range(20):
            _ = await hb_mgr.build_heartbeat_message()
        return (time.perf_counter() - t0) * 1000

    t_hb_20 = asyncio.run(bench_hb())
    ms_per_hb = t_hb_20 / 20
    results["heartbeat_assembly_ms"] = round(ms_per_hb, 3)
    print(f"[*] Heartbeat Snapshot Build:   {ms_per_hb:7.3f} ms / message")

    # Resource Profile
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    mem_info = process.memory_info()

    results["rss_mb"] = round(mem_info.rss / (1024 * 1024), 2)
    results["traced_peak_kb"] = round(peak_mem / 1024, 2)
    print("-" * 60)
    print(f"[*] Cloud Benchmark Peak Heap:  {results['traced_peak_kb']:7.2f} KB")
    print(f"[*] Process RSS Memory:          {results['rss_mb']:7.2f} MB")
    print("=" * 60)

    return results


if __name__ == "__main__":
    res = run_benchmark()
    if "--json" in sys.argv:
        print(json.dumps(res, indent=2))
