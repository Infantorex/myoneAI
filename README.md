# myoneAI — Tamil JARVIS 🎙️🤖

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/Infantorex/myoneAI/releases/tag/v1.0.0)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Hardware Optimization](https://img.shields.io/badge/Target-8GB%20RAM%20%7C%20Intel%20i3-orange.svg)]()
[![Tests](https://img.shields.io/badge/Tests-268%20passing-brightgreen.svg)]()
[![Security Audit](https://img.shields.io/badge/Security-100%25%20Verified-brightgreen.svg)](security/phase14-complete-security-audit.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **myoneAI** is an ultra-lightweight, local-first personal AI assistant and Tamil companion (**Tamil JARVIS**) engineered specifically for personal laptops with strict resource constraints (8 GB RAM, Intel Core i3 10th Gen, Windows 10/11).

---

## 🚀 Key Features & Capabilities

- **🎙️ Natural Voice Loop (Phases 2, 3, 5)**: Continuous hands-free voice loop supporting pure Tamil (`ta-IN`), English, and mixed Tanglish speech with fast cloud STT and Microsoft Edge Neural TTS (`ta-IN-PallaviNeural`).
- **⚡ Lightweight Wake Word (Phase 6)**: Low-power continuous acoustic/energy listener (< 0.5% idle CPU) activating on *"JARVIS"* or *"ஜார்விஸ்"*.
- **🧠 AI Reasoning Engine (Phase 4)**: Cloud LLM intelligence (Gemini 1.5 Flash / OpenAI / Groq) with friendly Tamil JARVIS persona, 12-turn FIFO bounded history, and zero heavy local models.
- **💾 Controlled AI Memory (Phase 7)**: SQLite persistence (`data/memory.db`) for preferences and project facts with token-based retrieval and automatic sensitive-credential blocking (passwords, OTPs, API keys).
- **🛡️ Secure PC Assistant Tools (Phase 8)**: Controlled application launches, browser navigation, volume/media keys, workspace filesystem tools, and on-demand screenshots governed by a strict 3-tier permission model (`SAFE`, `CONFIRM`, `BLOCKED`).
- **📊 System Monitoring & Diagnosis (Phase 9)**: On-demand CPU, RAM, Disk, Battery, and Network telemetry with non-spam threshold alert deduplication and slow-PC diagnostics (*"Why is my laptop slow?"*).
- **🗓️ Local Productivity Suite (Phase 10)**: SQLite tasks with priorities, natural date/time scheduled reminders, recurring daily/weekly reminders, full-text searchable notebook, and async countdown timers.
- **🌐 Local Web Dashboard (Phase 11)**: Responsive dark-mode dashboard (FastAPI backend + Vanilla JS/HTML5) on `http://127.0.0.1:8000` with telemetry gauges, dynamic orb visualizer, and text chat.
- **☁️ Secure Laptop ↔ Vercel Communication (Phase 12)**: Outbound-only HMAC-SHA256 authenticated cloud bridge with sliding-window replay attack protection, offline event queuing, and local air-gapped security enforcement.
- **🚀 Performance Optimized (Phase 13)**: Startup time < 1.0s, idle RAM < 85MB, active turn RAM < 180MB, SQLite WAL pragmas, and vectorized RMS VAD calculations.
- **🔒 Fully Tested & Audited (Phases 14 & 15)**: 268 automated tests (100% pass rate), 13-point security audit, automated backup/restore utilities, and single-instance cross-process lock.

---

## 🏛️ System Architecture

```text
                    ┌────────────────────────┐
                    │      Vercel Cloud      │
                    │   Dashboard / Control  │
                    └───────────┬────────────┘
                                │
                          HTTPS / WSS (HMAC-SHA256)
                                │
                                ▼
┌────────────────────────────────────────────────────────────┐
│                    WINDOWS LAPTOP RUNTIME                  │
│                                                            │
│   ┌──────────────┐      ┌─────────────┐     ┌───────────┐  │
│   │  Wake Word   │ ───► │  Tamil STT  │ ──► │  AI Core  │  │
│   │  ("JARVIS")  │      │ (Cloud API) │     │  Engine   │  │
│   └──────────────┘      └─────────────┘     └─────┬─────┘  │
│                                                   │        │
│                                                   ▼        │
│  ┌──────────────┐       ┌─────────────┐     ┌───────────┐  │
│  │   Speaker    │ ◄───  │  Tamil TTS  │ ◄── │  Memory & │  │
│  │ (In-memory)  │       │ (Neural HD) │     │  Tools    │  │
│  └──────────────┘       └─────────────┘     └─────┬─────┘  │
│                                                   │        │
│                                                   ▼        │
│                                       ┌──────────────────┐ │
│                                       │ Permission Layer │ │
│                                       │ SAFE/CONFIRM/BLK │ │
│                                       └─────────┬────────┘ │
│                                                 │          │
│            ┌────────────────────────────────────┴──┐       │
│            ▼                                       ▼       │
│   ┌──────────────────┐                   ┌────────────────┐│
│   │ Local Productivity│                  │ Hardware Health││
│   │ Tasks, Reminders │                  │ Monitoring     ││
│   │ Notes, Timers    │                  │ CPU, RAM, Disk ││
│   │ (SQLite Store)   │                  │ (psutil engine)││
│   └──────────────────┘                   └────────────────┘│
└────────────────────────────────────────────────────────────┘
```

---

## 💻 Hardware Requirements

| Component | Minimum Specification | Recommended Specification |
| :--- | :--- | :--- |
| **Operating System** | Windows 10 (64-bit) | Windows 11 (64-bit) |
| **Processor** | Intel Core i3 10th Gen U-series | Intel Core i3 / i5 / i7 or AMD Ryzen |
| **Memory (RAM)** | 8 GB RAM | 8 GB or 16 GB RAM |
| **Disk Space** | 250 MB free storage | 500 MB free storage |
| **Audio Hardware** | Standard laptop microphone & speakers | Standard microphone & speakers |

---

## ⚡ Quick Start & Installation

### 1. Clone & Setup
```powershell
git clone https://github.com/Infantorex/myoneAI.git
cd myoneAI

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Edit `.env` and add your cloud AI API key (e.g. `AI_API_KEY=AIzaSy...`).

### 3. Run Pre-Flight Diagnostics
```powershell
python -m app.core.health
```

### 4. Start JARVIS
```powershell
# Quick start using Windows launcher:
scripts\start_myoneai.bat

# Or run directly in Python:
python -m app.voice.jarvis
```

Say **"JARVIS"** or **"ஜார்விஸ்"** to activate hands-free speech!

---

## 🕹️ Windows Runtime Scripts

The `scripts/` directory provides one-click batch utilities for managing myoneAI:

| Script | Purpose |
| :--- | :--- |
| **`scripts\start_myoneai.bat`** | Runs pre-flight health checks and launches hands-free JARVIS assistant. |
| **`scripts\stop_myoneai.bat`** | Safely terminates active JARVIS processes and releases single-instance locks. |
| **`scripts\restart_myoneai.bat`** | Gracefully shuts down and restarts JARVIS. |
| **`scripts\health_check.bat`** | Runs full 11-subsystem health diagnostic report. |
| **`scripts\update_myoneai.bat`** | Creates backup, pulls latest Git release, updates packages, and runs test suite. |

---

## 💾 Backup & Data Restore

### Backup
```powershell
python scripts/backup_data.py
```
Creates a timestamped, sanitized `.zip` archive containing `memory.db`, `productivity.db`, and manifest metadata in `backups/`.

### Restore
```powershell
python scripts/restore_data.py --backup-file backups/myoneai_backup_v1.0.0_XXXXXX.zip
```
Validates archive manifest and verifies SQLite database integrity before restoring.

---

## 🧪 Automated Testing Suite (268 Tests)

Run the full automated test suite across all subsystems:

```powershell
pytest -v
```

```text
====================== 268 passed in 33.16s =======================
```

---

## 📚 Complete Documentation Suite

- 📖 [Installation Guide](docs/installation.md) — Detailed setup instructions
- ⚙️ [Configuration Guide](docs/configuration.md) — Complete `.env` reference
- 🎙️ [Usage & Voice Commands](docs/usage.md) — Complete list of voice intents in Tamil & English
- 🔧 [Troubleshooting Guide](docs/troubleshooting.md) — Audio, network, and API fixes
- 🛡️ [Security Architecture](docs/security.md) — Permission tiers, sandboxing & defenses
- 🔒 [Privacy Policy](docs/privacy.md) — Ephemeral audio and credential isolation guarantees
- 🏛️ [System Architecture](docs/architecture.md) — Deep-dive into internal modules
- 🔄 [Rollback Guide](docs/rollback.md) — Safe version rollback procedures
- ✅ [v1.0.0 Release Checklist](docs/v1.0.0-release-checklist.md) — Formal sign-off matrix

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
