"""AI conversation and memory performance benchmark for myoneAI.

Measures memory lookup latency, prompt construction, conversation turns, history trimming, and memory growth.
"""

import asyncio
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

from app.ai.manager import ConversationManager
from app.ai.models import ChatMessage
from app.ai.provider import MockAIProvider
from app.core.memory.manager import MemoryManager
from app.core.memory.models import MemoryItem
from app.core.memory.store import SQLiteMemoryStore


def run_benchmark():
    tracemalloc.start()
    process = psutil.Process(os.getpid())
    results = {}

    print("=" * 60)
    print("myoneAI — AI Engine & Memory Performance Benchmark")
    print("=" * 60)

    # 1. SQLite Memory Store Benchmarks
    test_db = PROJECT_ROOT / "data" / "perf_bench_memory.db"
    if test_db.exists():
        test_db.unlink()

    store = SQLiteMemoryStore(db_path=test_db)
    # Insert 100 sample memories
    t0 = time.perf_counter()
    for i in range(100):
        store.save(MemoryItem(
            category="preference" if i % 2 == 0 else "project",
            key=f"item_{i}",
            value=f"Performance benchmark stored value number {i} for user query testing",
            source="user",
            confidence=0.95,
        ))
    t_insert_100 = (time.perf_counter() - t0) * 1000
    results["memory_store_100_inserts_ms"] = round(t_insert_100, 2)
    results["memory_store_per_insert_ms"] = round(t_insert_100 / 100, 3)
    print(f"[*] Memory 100 Upserts:         {t_insert_100:7.2f} ms ({results['memory_store_per_insert_ms']:.3f} ms/upsert)")

    # 2. Memory Keyword Search Latency (100 iterations)
    t0 = time.perf_counter()
    for _ in range(100):
        _ = store.search(query="benchmark stored value", limit=5)
    t_search_100 = (time.perf_counter() - t0) * 1000
    results["memory_search_100_queries_ms"] = round(t_search_100, 2)
    results["memory_search_per_query_ms"] = round(t_search_100 / 100, 3)
    print(f"[*] Memory 100 Keyword Searches:{t_search_100:7.2f} ms ({results['memory_search_per_query_ms']:.3f} ms/search)")

    # 3. Memory Retrieval & Context Assembly
    mem_mgr = MemoryManager(db_path=test_db)
    t0 = time.perf_counter()
    for _ in range(100):
        _ = mem_mgr.get_context_for_prompt("What is the project info item_42?")
    t_ctx_100 = (time.perf_counter() - t0) * 1000
    results["memory_prompt_context_ms"] = round(t_ctx_100 / 100, 3)
    print(f"[*] Memory Context Formatting:  {results['memory_prompt_context_ms']:7.3f} ms / prompt")

    # 4. Conversation History FIFO Trimming Speed
    conv = ConversationManager(
        provider=MockAIProvider(default_response="வணக்கம்! நான் உங்களுக்கு உதவ தயார்."),
        memory=mem_mgr,
        max_history_messages=20,
    )

    t0 = time.perf_counter()
    for i in range(200):
        conv._history.append(ChatMessage(role="user", content=f"Message {i}"))
        conv._history.append(ChatMessage(role="assistant", content=f"Reply {i}"))
        conv._trim_history()
    t_trim = (time.perf_counter() - t0) * 1000
    results["history_trim_400_items_ms"] = round(t_trim, 3)
    print(f"[*] History Bounded Trimming:   {t_trim:7.3f} ms (400 items -> bounded {conv.history_length})")

    # 5. Full Conversational Turn Latency (50 iterations)
    async def run_turns():
        latencies = []
        for i in range(50):
            t_start = time.perf_counter()
            _ = await conv.respond(f"வணக்கம் JARVIS, சோதனை வினவல் எண் {i}")
            latencies.append((time.perf_counter() - t_start) * 1000)
        return latencies

    turn_latencies = asyncio.run(run_turns())
    avg_turn = sum(turn_latencies) / len(turn_latencies)
    results["avg_conversation_turn_ms"] = round(avg_turn, 2)
    results["min_conversation_turn_ms"] = round(min(turn_latencies), 2)
    results["max_conversation_turn_ms"] = round(max(turn_latencies), 2)
    print(f"[*] AI Conversational Turn:     {avg_turn:7.2f} ms (min: {results['min_conversation_turn_ms']}ms, max: {results['max_conversation_turn_ms']}ms)")

    # Cleanup test db
    del store
    del mem_mgr
    del conv
    import gc
    gc.collect()
    try:
        if test_db.exists():
            test_db.unlink()
    except Exception:
        pass

    # Resource Profile
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    mem_info = process.memory_info()

    results["rss_mb"] = round(mem_info.rss / (1024 * 1024), 2)
    results["traced_peak_kb"] = round(peak_mem / 1024, 2)
    print("-" * 60)
    print(f"[*] AI Benchmark Peak Heap:     {results['traced_peak_kb']:7.2f} KB")
    print(f"[*] Process RSS Memory:          {results['rss_mb']:7.2f} MB")
    print("=" * 60)

    return results


if __name__ == "__main__":
    res = run_benchmark()
    if "--json" in sys.argv:
        print(json.dumps(res, indent=2))
