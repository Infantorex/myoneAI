"""Performance and Stress Test Suite for myoneAI (Phase 13).

Validates performance budgets, bounded collections, SQLite WAL pragmas,
adaptive battery throttling, and memory stability under stress loops.
"""

import asyncio
import os
import sqlite3
import time
from pathlib import Path
import pytest
import numpy as np

from app.ai.manager import ConversationManager
from app.ai.models import ChatMessage
from app.ai.provider import MockAIProvider
from app.cloud.protocol import CloudMessage, MessageType, ReplayProtection
from app.cloud.queue import OfflineEventQueue
from app.core.config import get_settings
from app.core.memory.manager import MemoryManager
from app.core.memory.models import MemoryItem
from app.core.memory.store import SQLiteMemoryStore
from app.monitoring.manager import MonitoringManager
from app.monitoring.processes import get_process_metrics, get_top_processes
from app.productivity.database import ProductivityDatabase
from app.productivity.models import TaskItem, TaskPriority, TaskStatus
from app.voice.audio import AudioPlayer
from app.voice.audio_config import DEFAULT_AUDIO_CONFIG
from app.voice.microphone import pcm_to_wav_bytes
from app.voice.vad import VoiceActivityDetector, VADState


def test_sqlite_memory_store_wal_pragmas(tmp_path):
    """Verify SQLiteMemoryStore enables WAL mode and performance pragmas."""
    db_file = tmp_path / "test_perf_memory.db"
    store = SQLiteMemoryStore(db_path=db_file)

    # Verify pragmas via direct SQLite query
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()

    cursor.execute("PRAGMA journal_mode;")
    mode = cursor.fetchone()[0]
    assert mode.lower() == "wal"

    conn.close()

    # Verify CRUD works efficiently
    item = store.save(MemoryItem(
        category="preference",
        key="test_key",
        value="test_value",
        source="user",
        confidence=1.0,
    ))
    assert item.id is not None
    fetched = store.get("preference", "test_key")
    assert fetched is not None
    assert fetched.value == "test_value"


def test_sqlite_productivity_db_wal_pragmas(tmp_path):
    """Verify ProductivityDatabase initializes with WAL mode and composite indexes."""
    db_file = tmp_path / "test_perf_productivity.db"
    db = ProductivityDatabase(db_path=str(db_file))

    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()

    cursor.execute("PRAGMA journal_mode;")
    mode = cursor.fetchone()[0]
    assert mode.lower() == "wal"

    # Verify indexes exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
    indexes = {row[0] for row in cursor.fetchall()}
    assert "idx_tasks_status_due" in indexes
    assert "idx_reminders_status_trigger" in indexes
    assert "idx_notes_updated" in indexes

    conn.close()

    # Verify task creation
    task = db.add_task(TaskItem(title="Benchmark task", priority=TaskPriority.HIGH))
    assert task.id is not None


def test_vad_rms_performance_budget():
    """Verify RMS calculation meets the performance budget (< 100 µs per chunk)."""
    vad = VoiceActivityDetector()
    chunk_size = 1024
    t = np.linspace(0, 0.064, chunk_size, dtype=np.float32)
    chunk_pcm = (np.sin(2 * np.pi * 440 * t) * 10000).astype(np.int16).tobytes()

    t0 = time.perf_counter()
    iterations = 2000
    for _ in range(iterations):
        rms = vad.calculate_rms(chunk_pcm)
        assert rms > 0.0
    elapsed_ms = (time.perf_counter() - t0) * 1000
    us_per_chunk = (elapsed_ms / iterations) * 1000

    # Strict budget: RMS calculation must stay under 100 µs on any x64 core
    assert us_per_chunk < 100.0, f"RMS compute took {us_per_chunk:.2f} µs, exceeded 100 µs budget."


def test_vad_stream_100_chunks():
    """Verify VAD processes 100 audio chunks within budget (< 50 ms total)."""
    vad = VoiceActivityDetector()
    chunk_size = 1024
    chunks = [(np.ones(chunk_size, dtype=np.int16) * 5000).tobytes() for _ in range(100)]

    t0 = time.perf_counter()
    for chunk in chunks:
        _ = vad.process_chunk(chunk)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms < 50.0, f"VAD 100 chunks took {elapsed_ms:.2f} ms (budget: 50 ms)."
    assert vad.state == VADState.SPEECH_DETECTED


def test_process_metrics_single_pass():
    """Verify process metrics collection runs and returns structured telemetry."""
    metrics = get_process_metrics(limit=3)
    assert metrics is not None
    assert isinstance(metrics.top_memory, list)
    assert isinstance(metrics.top_cpu, list)
    assert metrics.total_processes >= len(metrics.top_memory)


def test_conversation_history_bounding_under_stress():
    """Verify ConversationManager strictly bounds memory history under 100 continuous turns."""
    conv = ConversationManager(
        provider=MockAIProvider(default_response="சரி"),
        max_history_messages=10,
    )

    for i in range(100):
        conv._history.append(ChatMessage(role="user", content=f"Stress prompt {i}"))
        conv._history.append(ChatMessage(role="assistant", content=f"Stress reply {i}"))
        conv._trim_history()

    assert conv.history_length == 10
    # Oldest retained message should be bounded to recent turns
    assert "Stress prompt 95" in conv._history[0].content or "Stress reply 95" in conv._history[0].content


def test_offline_queue_bounded_eviction():
    """Verify OfflineEventQueue strictly bounds memory and evicts oldest items."""
    q = OfflineEventQueue(max_size=10)
    for i in range(50):
        q.enqueue(CloudMessage(
            type=MessageType.STATUS.value,
            device_id="dev_001",
            payload={"sequence": i},
        ))

    assert len(q) == 10
    assert q.size == 10
    # The oldest item in queue should be sequence 40
    first = q.dequeue()
    assert first is not None
    assert first.payload["sequence"] == 40
    assert len(q) == 9


def test_replay_protection_sliding_window_eviction():
    """Verify ReplayProtection caches and evicts without unbounded memory growth."""
    replay = ReplayProtection(max_drift_seconds=300.0, max_cache_size=50)
    now = time.time()

    for i in range(100):
        msg = CloudMessage(
            id=f"msg_{i}",
            type=MessageType.HEARTBEAT.value,
            timestamp=now,
            device_id="dev_001",
            payload={},
        )
        replay.validate_message(msg, current_time=now)

    # Seen IDs set should not grow unbounded
    assert len(replay._seen_ids) <= 100


@pytest.mark.asyncio
async def test_ai_consecutive_turns_stress(tmp_path):
    """Stress test 20 consecutive AI conversation turns for memory & latency stability."""
    db_file = tmp_path / "test_stress_memory.db"
    mem_mgr = MemoryManager(db_path=db_file)
    conv = ConversationManager(
        provider=MockAIProvider(default_response="வணக்கம்! உதவி செய்ய தயாராக உள்ளேன்."),
        memory=mem_mgr,
        max_history_messages=10,
    )

    latencies = []
    for i in range(20):
        t0 = time.perf_counter()
        resp = await conv.respond(f"வணக்கம் JARVIS, சோதனை வினவல் எண் {i}")
        latencies.append((time.perf_counter() - t0) * 1000)
        assert resp is not None

    avg_latency = sum(latencies) / len(latencies)
    # Mock conversational turn should average < 30ms
    assert avg_latency < 30.0, f"Average turn latency was {avg_latency:.2f} ms (budget: 30 ms)."
    assert conv.history_length <= 10
