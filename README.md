# myoneAI — Tamil JARVIS 🎙️🤖

[![Python 3.12](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Modular%20%26%20Async-brightgreen.svg)]()
[![Hardware Optimization](https://img.shields.io/badge/Target-8GB%20RAM%20%7C%20Intel%20i3-orange.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **myoneAI** is an ultra-lightweight, resource-efficient personal AI assistant and Tamil companion (Tamil JARVIS) designed specifically for personal laptops with strict hardware constraints (8 GB RAM, Intel Core i3 10th Gen, Windows).

---

## 🚀 Key Capabilities

- **Secure Laptop ↔ Vercel Communication (Phase 12)**: Secure outbound HTTPS/WSS communication bridge connecting the local Windows assistant with the Vercel-hosted Cloud Control Plane and Dashboard. Features cryptographic HMAC-SHA256 request signing, sliding-window replay attack prevention (300s window), local `PermissionManager` tier enforcement (SAFE, CONFIRM, BLOCKED), non-blocking offline resilience with exponential backoff (2s → 60s), bounded safe event queuing (max 100 items), and zero open inbound ports on the laptop.
- **Local Web Dashboard (Phase 11)**: Modern, lightweight dark-mode browser dashboard (FastAPI backend + Vanilla HTML5/CSS3/JS) for monitoring system telemetry (CPU, RAM, Disk, Battery, Network), live assistant state visualization (Idle, Listening, Thinking, Speaking), text chat with Tamil JARVIS, full CRUD for tasks, reminders, notes, and memory, sanitized activity feed, and safe configuration management. Binds strictly to `127.0.0.1:8000` with zero public exposure and optional Bearer token auth.
- **Productivity & Personal Task System (Phase 10)**: 100% local, SQLite-backed task and productivity system (`data/productivity.db`). Supports priority-ranked tasks, natural date/time scheduled reminders ("Remind me tomorrow at 9 AM", "10 minutes-ல் நினைவூட்டு"), daily/weekly recurring reminders, notebook entries with keyword search, async in-memory timers, startup missed reminder recovery, and confirmation-guarded bulk actions.
- **Lightweight System Monitoring & Alerts (Phase 9)**: Real-time, on-demand hardware telemetry across CPU, RAM, Disk, Battery, Network, and Top Processes. Features configurable threshold detection (`WARNING`, `CRITICAL`), alert deduplication cooldown (`ALERT_COOLDOWN_SECONDS=300`), intelligent slow system diagnosis ("Why is my laptop slow?"), bilingual English/Tamil voice responses, and zero continuous background polling.
- **Secure PC Assistant Tools (Phase 8)**: Controlled, safe PC actions (Application launch/termination, web browser search/navigation, workspace filesystem browsing, volume/media controls, on-demand screenshots with automatic 7-day retention, and system telemetry) with centralized permission tiers (`SAFE`, `CONFIRM`, `BLOCKED`), confirmation timeout safeguards, and zero arbitrary shell access.
- **Controlled AI Memory (Phase 7)**: Persistent, privacy-aware SQLite memory storing user preferences, project facts, and context across sessions with natural language memory commands ("Remember that...", "What do you remember about me?", "Forget that...") and automated sensitive-credential blocking.
- **Lightweight Wake Word System (Phase 6)**: Hands-free activation via "JARVIS" wake phrase with low-power local acoustic/energy evaluation (< 0.5% idle CPU), debounced cooldown protection, and seamless microphone ownership handover.
- **Natural Voice Conversation Loop (Phase 5)**: Complete end-to-end conversational pipeline connecting Microphone → Speech Detection (VAD) → Tamil STT → AI Conversation Engine → Tamil TTS → Speaker playback.
- **AI Brain & Natural Conversation (Phase 4)**: Context-aware conversational intelligence supporting pure Tamil (`ta-IN`), English, and mixed Tanglish code-switching with concise, friendly JARVIS persona.
- **Tamil Speech Recognition (STT)**: Fast cloud transcription for Tamil, English, and Tanglish with on-demand Voice Activity Detection (VAD).
- **Natural Tamil Voice Synthesis (TTS)**: High-definition neural speech (`ta-IN-PallaviNeural`, `ta-IN-ValluvarNeural`) with 100% in-memory audio streaming.
- **Hardware-First Resource Efficiency**:
  - **Zero Heavy Local LLMs / Vector DBs**: Pure SQLite local store + Cloud API inference.
  - **Zero Heavy External Servers**: No Redis, MongoDB, or background daemon servers.
  - **Zero Heavy Browser Drivers / Screen Recorders**: Direct Windows GDI screen capture & lightweight OS integration without Playwright or Selenium.
  - **Zero Continuous Cloud Audio Upload**: Background wake listening evaluates audio locally without streaming ambient sound to cloud APIs.
  - **Ultra-Low Memory Footprint**: Baseline memory footprint is **~48.5 MB RAM** with zero background polling.
  - **Bounded Context**: Hard limits on memory, notes, and task token context prevent token bloat.
  - **100% In-Memory Audio & Timers**: Audio buffers and countdown timers run purely in volatile RAM.
- **Strict Security Boundaries**:
  - ⚠️ **myoneAI cannot execute arbitrary shell commands.**
  - Zero `eval()`, `exec()`, `shell=True`, or dynamic command line generation from model output.
  - Risky actions (file deletion, app termination, task/note deletion) require explicit user confirmation with short timeout expiration.
  - No automatic destructive actions during system monitoring or task management.

> [!IMPORTANT]
> **CRITICAL SECURITY GUARANTEE**: The AI model has no shell execution privileges. It can only call explicitly allowlisted tools defined in `ToolRegistry`. Dangerous actions (`delete_file`, `delete_task`, `clear_all_tasks`, `close_application`) require explicit user confirmation before execution.

---

## 🏛️ System Architecture

```text
User Speech / Text
       ↓
Wake Word Detector ("JARVIS")
       ↓
Intent Detection (Natural Tamil / English Parser)
       ↓
Permission Manager (SAFE / CONFIRM / BLOCKED)
       ↓
Approved Tool Execution (Tasks, Reminders, Notes, Timers, Monitoring, Apps, Browser, FS, Media)
       ↓
Structured Tool Result / SQLite Persistent State
       ↓
AI Conversation Manager (Persona + Context Synthesis)
       ↓
AI Provider (Gemini / OpenAI / Groq)
       ↓
Tamil Neural TTS (`ta-IN-PallaviNeural`)
       ↓
Speaker Audio Playback
```

---

## 📁 Project Structure

```text
myoneAI/
├── app/
│   ├── __init__.py                         # Version and metadata
│   ├── core/                               # Core runtime & lifecycle
│   │   ├── __init__.py
│   │   ├── config.py                       # Pydantic BaseSettings, env validation & thresholds
│   │   ├── logging_config.py               # Rotating log handler & credential redactor
│   │   ├── events.py                       # Pub-sub async event bus
│   │   ├── state.py                        # State machine & telemetry
│   │   ├── main.py                         # CLI entrypoint & diagnostic engine
│   │   └── memory/                         # Controlled AI Memory System (Phase 7)
│   ├── ai/                                 # AI Conversation Engine (Phase 4)
│   │   ├── __init__.py
│   │   ├── errors.py                       # Structured AI & provider exceptions
│   │   ├── manager.py                      # Conversation manager & tool/memory orchestrator
│   │   ├── models.py                       # ChatMessage, AIRequestConfig, AIResponse schemas
│   │   ├── prompts.py                      # JARVIS Tamil persona & No-Fake-Actions rules
│   │   ├── provider.py                     # Provider abstraction (Gemini, OpenAI, Mock)
│   │   └── test_ai.py                      # Interactive & CLI chat test utility
│   ├── monitoring/                         # Lightweight System Monitoring & Alerts (Phase 9)
│   │   ├── __init__.py                     # Subsystem exports & aliases
│   │   ├── models.py                       # CPUMetrics, MemoryMetrics, DiskMetrics, MonitoringSnapshot
│   │   ├── manager.py                      # MonitoringManager (async snapshots & periodic alerts)
│   │   ├── cpu.py                          # On-demand CPU utilization & core topology
│   │   ├── memory.py                       # Physical RAM breakdown & used/free MB
│   │   ├── disk.py                         # Primary partition capacity & free GB
│   │   ├── battery.py                      # Power state & desktop non-crashing fallback
│   │   ├── network.py                      # Socket-based connectivity & latency telemetry
│   │   ├── processes.py                    # Top resource-consuming processes on demand
│   │   ├── thresholds.py                   # ThresholdEngine (WARNING / CRITICAL rules)
│   │   ├── alerts.py                       # AlertManager & 300s cooldown deduplication
│   │   └── test_monitoring.py              # CLI demonstration & test runner
│   ├── productivity/                       # Productivity & Task System (Phase 10)
│   │   ├── __init__.py                     # Clean productivity exports
│   │   ├── models.py                       # TaskItem, ReminderItem, NoteItem, ActiveTimer schemas
│   │   ├── database.py                     # SQLite persistent storage manager (data/productivity.db)
│   │   ├── manager.py                      # Unified ProductivityManager facade
│   │   ├── tasks.py                        # Task CRUD, priorities (HIGH/MEDIUM/LOW), statuses
│   │   ├── reminders.py                    # Natural date/time parser & daily/weekly recurrence
│   │   ├── notes.py                        # Notebook entries with keyword search and tagging
│   │   ├── timers.py                       # In-memory async countdown timers
│   │   ├── scheduler.py                    # Background reminder scheduler & startup recovery
│   │   └── test_productivity.py           # Standalone test runner and demonstration
│   ├── tools/                              # Secure PC Assistant Tools (Phases 8, 9 & 10)
│   │   ├── __init__.py
│   │   ├── registry.py                     # ToolRegistry & schema registrations
│   │   ├── schemas.py                      # ToolSchema, ToolCall, ToolResult dataclasses
│   │   ├── executor.py                     # ToolExecutor & timeout / error handling
│   │   ├── intent.py                       # Tamil / English intent detection parser
│   │   ├── productivity.py                 # Task, reminder, note, and timer tool handlers
│   │   ├── applications.py                 # Safe application launch & close handlers
│   │   ├── browser.py                      # Safe HTTP/HTTPS web navigation & search
│   │   ├── filesystem.py                   # Bounded folder browsing & safe file operations
│   │   ├── media.py                        # Native Windows volume & playback keys
│   │   ├── screenshot.py                   # Native Windows GDI screen snapshot & cleanup
│   │   └── system.py                       # Safe CPU, RAM, Disk, Battery, Network & Diagnosis tools
│   ├── security/                           # Centralized Security & Permissions (Phase 8)
│   │   ├── __init__.py
│   │   ├── policies.py                     # Application/directory allowlists & blocked paths
│   │   ├── permissions.py                  # SAFE/CONFIRM/BLOCKED manager & tokens
│   │   └── audit.py                        # Structured security audit logger
│   └── voice/                              # Voice, STT, TTS, Wake Word & Conversation Loop
├── docs/
│   ├── phase7-privacy.md                   # AI Memory privacy & credential policies
│   ├── phase8-performance.md               # PC Tools resource benchmarks & latency
│   ├── phase8-privacy.md                   # PC Tools data boundaries & privacy policies
│   ├── phase9-performance.md               # Monitoring latency, CPU/RAM benchmarks
│   ├── phase9-privacy.md                   # Telemetry collection boundaries & retention
│   ├── phase10-performance.md              # Productivity DB & scheduler benchmarks
│   └── phase10-privacy.md                  # Task, reminder, and note privacy guarantees
├── security/
│   ├── phase7-memory-audit.md              # AI Memory security audit checklist
│   ├── phase8-tools-audit.md               # PC Tools security & safety audit checklist
│   ├── phase9-monitoring-audit.md          # Monitoring & alert security audit checklist
│   └── phase10-productivity-audit.md       # Productivity system security audit checklist
├── tests/                                  # 158 automated unit/integration tests (0 failed)
│   ├── test_productivity.py                # Phase 10 Productivity comprehensive tests
│   ├── test_monitoring.py                  # Phase 9 Monitoring comprehensive tests
│   ├── test_tools.py                       # Phase 8 PC Tools comprehensive tests
│   └── ...
├── .env.example                            # Configuration template
├── pytest.ini                              # Pytest configuration
├── requirements.txt                        # Lightweight dependencies
└── README.md
```

---

## 🗓️ Productivity & Personal Task System (Phase 10)

### Available Productivity Tools & Voice Commands

| Tool Name | Permission Level | Description | Example Voice Command |
| :--- | :---: | :--- | :--- |
| **`create_task`** | `SAFE` | Add a priority-ranked task to todo list | *"Add a task to finish my PPT"* / *"PPT complete பண்ணணும், task add பண்ணு"* |
| **`list_tasks`** | `SAFE` | List active tasks with priorities and deadlines | *"What are my tasks today?"* / *"இன்னைக்கு என்ன tasks இருக்கு?"* |
| **`complete_task`** | `SAFE` | Mark a task as completed by ID or title | *"Mark PCB design as completed"* / *"இந்த task complete பண்ணு"* |
| **`delete_task`** | `CONFIRM` | Permanently remove a task | *"Delete the presentation task"* (Requires confirmation) |
| **`clear_all_tasks`** | `CONFIRM` | Clear all saved tasks | *"Delete all my tasks"* (Requires confirmation) |
| **`create_reminder`** | `SAFE` | Schedule reminder with natural date/time | *"Remind me at 6 PM to submit the report"* / *"நாளைக்கு PPT submit பண்ணணும், reminder வை"* |
| **`list_reminders`** | `SAFE` | List pending and recurring reminders | *"What reminders do I have?"* / *"என்ன reminders இருக்கு?"* |
| **`cancel_reminder`** | `CONFIRM` | Cancel scheduled reminder | *"Cancel my reminder"* (Requires confirmation) |
| **`create_note`** | `SAFE` | Save note to local notebook | *"Take a note: buy Arduino components"* / *"குறிப்பு எடு: ..."* |
| **`list_notes`** | `SAFE` | List recently updated notes | *"Show my notes"* / *"குறிப்புகளை காட்டு"* |
| **`search_notes`** | `SAFE` | Search notebook by keyword | *"Search my notes for PCB"* |
| **`delete_note`** | `CONFIRM` | Delete note from notebook | *"Delete note Arduino"* (Requires confirmation) |
| **`create_timer`** | `SAFE` | Start in-memory countdown timer | *"Set a timer for 10 minutes"* / *"10 minutes timer வை"* |
| **`cancel_timer`** | `SAFE` | Stop running countdown timer | *"Cancel my timer"* / *"timer cancel பண்ணு"* |
| **`get_timer_status`** | `SAFE` | Check remaining time on active timer | *"How much time is left?"* / *"timer எவ்வளவு நேரம் இருக்கு?"* |

### Recurrence & Startup Recovery
- **Daily / Weekly Recurrence**: Saying *"Remind me every day at 8 AM to study"* automatically schedules recurring reminders that re-arm after triggering.
- **Missed Reminder Recovery**: If JARVIS was closed during a scheduled time, the scheduler checks missed reminders on startup (up to `MAX_MISSED_REMINDERS_ON_STARTUP=5`) without notification flooding.

---

## ⚡ Quick Start & Installation

### 1. Prerequisites
- **Python 3.12+**
- **Windows 10/11** (Intel i3 / 8GB RAM compatible)

### 2. Setup Virtual Environment
```powershell
# Clone repository
git clone https://github.com/Infantorex/myoneAI.git
cd myoneAI

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install lightweight dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Add your API key (e.g. `AI_API_KEY=your_gemini_api_key_here`).

---

## 🌐 Local Web Dashboard (Phase 11)

### 1. Launching the Web Dashboard
```powershell
# Start local FastAPI web server & dashboard:
python -m web.api.server
```

Open your browser to:
```text
http://127.0.0.1:8000
```

### 2. Available Dashboard Pages & APIs
- **Dashboard Home**: Real-time CPU, RAM, Disk, Battery, Network metrics, task previews, memory summary, and sanitized activity feed.
- **Assistant & Chat**: JARVIS dynamic visualizer orb (Idle / Listening / Thinking / Speaking), voice controls, and text chat with rate-limiting and validation.
- **Tasks**: Full priority-ranked CRUD with TODO/COMPLETED status toggling.
- **Reminders**: Schedule single or recurring reminders with natural date/time parsing.
- **Notes**: Instant full-text searchable notebook entries with tag pills.
- **Memory**: Privacy-governed long-term memory view with confirmation-guarded clear all.
- **System**: Deep hardware diagnostics, warning engine, and top CPU/Memory process inspection.
- **Settings**: Safe configuration parameters and Bearer token management.

---

## 🤖 Hands-Free JARVIS Assistant Execution

```powershell
# Run full assistant with Wake Word, Voice, Memory, PC Tools, Monitoring & Tasks:
python -m app.voice.jarvis

# Offline simulation mode:
python -m app.voice.jarvis --mock

# Run productivity interactive test runner:
python -m app.productivity.test_productivity
```

---

## 🧪 Run Automated Tests (203 tests)

```powershell
pytest -v
```

---

## 📊 Performance Benchmarks (Phase 12)

| Subsystem | Metric | Measured Value | Threshold | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Cloud Bridge** | **HMAC-SHA256 Signing & Verification**| **~0.12 ms** | < 1.0 ms | 🟢 Constant-time Security |
| **Cloud Heartbeat** | **Outbound Telemetry Latency** | **~25 ms** | < 100 ms | 🟢 Ultra-low Duty Cycle |
| **Web Dashboard** | **Static Asset Load Time** | **~45 ms** | < 300 ms | 🟢 Instant Zero-Framework |
| **System** | **Startup RAM Footprint** | **~48.8 MB** | < 100 MB | 🟢 Ultra-Lightweight |
| **Productivity DB** | **Task / Reminder INSERT Latency** | **~0.45 ms** | < 10 ms | 🟢 Sub-millisecond SQLite |
| **Notebook Search** | **Note Full-Text Wildcard Search** | **~0.60 ms** | < 20 ms | 🟢 Near-instant Search |
| **Scheduler** | **Background Polling Duty Cycle CPU**| **< 0.001% CPU** | < 0.5% CPU | 🟢 Zero Idle Impact |
| **Tests** | **Unit & Integration Test Pass Rate**| **203 / 203 (100%)**| 100% | 🟢 All Pass (0 failed) |

---

## 🗺️ Development Roadmap

- [x] **Phase 1: Foundation** — Core config, logging, event bus, state machine, CLI diagnostics.
- [x] **Phase 2: Tamil STT** — Audio capture, VAD, Google/Groq STT providers, Mode 1/2/3 tests.
- [x] **Phase 3: Tamil TTS** — Microsoft Edge Neural TTS (`ta-IN-PallaviNeural`), in-memory audio player, overlap protection.
- [x] **Phase 4: AI Conversation** — Cloud LLM provider abstraction (Gemini / OpenAI), JARVIS Tamil persona, short-term context window, safety boundaries.
- [x] **Phase 5: Voice Conversation Loop** — Coordinated voice cycle (Idle → Record → STT → AI → TTS → Idle), interactive mode, mock simulation, and interrupt safety.
- [x] **Phase 6: Wake Word** — Low-power local wake word detection, debouncing cooldown, microphone ownership handover, and hands-free JARVIS runtime.
- [x] **Phase 7: Memory** — Controlled AI memory, SQLite persistence, relevance retrieval, privacy filter, natural memory commands.
- [x] **Phase 8: PC Tools** — Secure PC assistant tools, centralized permissions, application/browser/media/screenshot/telemetry tools, confirmation lifecycle, and audit logging.
- [x] **Phase 9: Lightweight System Monitoring & Alerts** — On-demand & periodic health telemetry, threshold evaluation, alert cooldown deduplication, slow PC diagnosis, and bilingual voice responses.
- [x] **Phase 10: Productivity & Personal Task System** — SQLite tasks, reminders, natural date/time parser, daily/weekly recurrence, notebook, async countdown timers, scheduler recovery.
- [x] **Phase 11: Web Dashboard** — Local FastAPI backend, responsive dark-mode JARVIS dashboard, telemetry & assistant control, text chat, task/reminder/note/memory management, localhost security.
- [x] **Phase 12: Laptop ↔ Vercel Communication** — Secure outbound HTTPS/WSS bridge, HMAC-SHA256 request signing, sliding replay protection, permission enforcement, bounded offline queue, Vercel cloud control plane API.
- [ ] **Phase 13: Optimization** — Fine-tuning CPU/RAM profiling.
- [ ] **Phase 14: Testing** — End-to-end integration tests.
- [ ] **Phase 15: Production Deployment** — Vercel web deployment & local agent service.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
