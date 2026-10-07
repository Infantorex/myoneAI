# Phase 13 — Performance Baseline Report

**System Environment:**
- **OS**: Windows 11 / Windows 10 x64
- **Target Hardware Architecture**: Intel Core i3 10th Gen U-series, 8 GB RAM
- **Runtime**: Python 3.12.10 (AMD64)
- **Measurement Date**: October 2026

---

## 1. Startup & Initialization Baseline

| Component | Time (ms) | Notes |
|---|---:|---|
| Configuration Loading (`get_settings()`) | 1147.19 | Pydantic BaseSettings & .env disk parsing |
| Core State & Events Init | < 0.01 | In-memory singleton registration |
| Security & Permissions Init | 13.52 | Allowlist policy parsing |
| Memory Subsystem Init | 40.88 | SQLite table check & schema init |
| Productivity Subsystem Init | 28.10 | SQLite tasks/reminders/notes tables |
| Tools Registry Init | 97.57 | Tool schemas and handlers registration |
| AI Conversation Manager Init | 359.67 | Prompts, providers, tools integration |
| Monitoring Manager Init | < 0.01 | Singleton initialization |
| Voice Subsystems Init | 1824.94 | EdgeTTS, sounddevice, miniaudio imports |
| Cloud Client Init | 21.61 | Identity & connection models |
| FastAPI Application & Routes Init | 1871.85 | Starlette/FastAPI route trees & middleware |
| **Total Subsystem Startup** | **5405.33 ms** | **~5.41 seconds cold initialization** |

### Process Baseline at Startup
- **Process RSS Memory**: 108.91 MB
- **Traced Python Peak Heap**: 37.99 MB
- **Active Threads**: 14

---

## 2. Voice Subsystem Baseline

| Operation | Latency / Throughput | Notes |
|---|---:|---|
| RMS Energy Compute | 35.18 µs / chunk | 28,426 chunks / sec throughput |
| VAD 100-chunk Stream Processing | 4.53 ms total (45.35 µs / chunk) | 6.4 seconds of synthetic speech |
| PCM -> WAV In-Memory Encoding | 0.172 ms | 200.0 KB buffer |
| Audio Player WAV Decode | 0.767 ms | 102,400 samples @ 16kHz |
| STT Engine Latency (Mock) | 0.014 ms | Deterministic benchmark |
| TTS Engine Latency (Mock) | 0.377 ms | Deterministic benchmark |
| Voice Peak Heap Allocation | 2.23 MB | Traced memory during streaming |
| Subsystem Process RSS | 79.32 MB | - |

---

## 3. AI Conversation & Memory Baseline

| Operation | Latency | Notes |
|---|---:|---|
| Memory 100 Upserts (SQLite) | 5185.50 ms (51.85 ms / upsert) | **Bottleneck**: Synchronous DELETE journal writes |
| Memory 100 Keyword Searches | 69.86 ms (0.699 ms / search) | SQLite wildcard query |
| Memory Context Prompt Formatting | 3.95 ms / prompt | Relevance ranking & string assembly |
| History FIFO Trimming (400 items) | 4.98 ms | Enforces bounded context |
| Full AI Conversational Turn | 7.05 ms (min: 4.3ms, max: 94.98ms) | Mock AI provider + tool check + memory |
| AI Subsystem Peak Heap | 331.47 KB | - |
| Subsystem Process RSS | 58.25 MB | - |

---

## 4. System Monitoring Baseline

| Telemetry Component | Latency | Notes |
|---|---:|---|
| CPU Metrics (Instant) | 0.543 ms | `psutil.cpu_percent(interval=None)` |
| CPU Metrics (Sampled 0.05s) | 50.57 ms | `psutil.cpu_percent(interval=0.05)` |
| Memory Metrics | 0.074 ms | `psutil.virtual_memory()` |
| Disk Metrics | 0.072 ms | `psutil.disk_usage()` |
| Battery Metrics | 0.010 ms | `psutil.sensors_battery()` |
| Network Metrics | 0.208 ms | Interface check |
| Process Metrics (Top 5) | 890.46 ms | **Bottleneck**: 287 processes scanned with 2 iterations |
| Full Snapshot (without processes) | 0.689 ms | Clean, lightweight telemetry |
| Threshold Engine Evaluation | 30.63 µs / eval | 1000 evaluations |
| Alert Manager Dispatch Check | 6.11 µs / check | 1000 checks |
| Subsystem Process RSS | 47.41 MB | - |

---

## 5. Cloud Communication Baseline

| Operation | Latency / Throughput | Notes |
|---|---:|---|
| HMAC-SHA256 Payload Signature | 49.24 µs / sign | ~20,310 ops / sec |
| Message Sign & Verify Roundtrip | 101.05 µs / roundtrip | Constant-time digest comparison |
| Replay Protection Filter | 176.56 µs / check | 10,000 unique checks |
| Offline Event Queue Enqueue | 53.68 µs / enqueue | Bounded size: 100 |
| Heartbeat Snapshot Build | 52.45 ms / message | Hardware snapshot + signature |
| Subsystem Process RSS | 54.22 MB | - |

---

## 6. Identified Bottlenecks & Optimization Plan

1. **SQLite Database Sync I/O**:
   - **Problem**: Default SQLite settings execute sync disk writes on every upsert (`DELETE` journal mode).
   - **Fix**: Apply `PRAGMA journal_mode = WAL;`, `PRAGMA synchronous = NORMAL;`, `PRAGMA cache_size = -2000;`, `PRAGMA temp_store = MEMORY;`. Add composite indexes.
2. **Process Metrics CPU Overhead**:
   - **Problem**: `get_process_metrics` called `process_iter` twice (once for memory, once for CPU), taking 890ms.
   - **Fix**: Single-pass process iteration with in-flight top-k heap/sort.
3. **Voice Pipeline RMS Computation**:
   - **Problem**: `samples.astype(np.float64) ** 2` creates intermediate copy array.
   - **Fix**: Optimize RMS calculation using `np.dot` or integer math where appropriate.
4. **FastAPI & Voice Startup Lazy Loading**:
   - **Problem**: Heavy modules (e.g. `edge_tts`, `miniaudio`, `speech_recognition`, `pyautogui`) imported at module root instead of on demand.
   - **Fix**: Ensure optional and heavy providers load cleanly without unnecessary import overhead.
5. **Dashboard Polling & Battery-Aware Monitoring**:
   - **Problem**: Browser polling every 10s even when tab is backgrounded.
   - **Fix**: Add Page Visibility API listener (`document.hidden`) to back off polling to 30s when inactive. Double monitoring interval when on battery.
