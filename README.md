# myoneAI — Tamil JARVIS 🎙️🤖

[![Python 3.12](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Modular%20%26%20Async-brightgreen.svg)]()
[![Hardware Optimization](https://img.shields.io/badge/Target-8GB%20RAM%20%7C%20Intel%20i3-orange.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **myoneAI** is an ultra-lightweight, resource-efficient personal AI assistant and Tamil companion (Tamil JARVIS) designed specifically for personal laptops with strict hardware constraints (8 GB RAM, Intel Core i3 10th Gen, Windows).

---

## 🚀 Key Objectives

- **Tamil & Tanglish Voice Assistant**: Understands pure Tamil, Tamil-English code-switching, Tanglish, and English; responds with natural Tamil speech.
- **Hardware-First Resource Efficiency**:
  - **Zero Heavy Local LLMs**: Utilizes lightweight Cloud API inference (Gemini / OpenAI).
  - **No Continuous Background Processing**: Microphone and heavy audio inference activate strictly on demand.
  - **Ultra-Low Memory Footprint**: Core runtime uses **< 45 MB RAM** at startup.
- **Provider-Independent Interfaces**: Modularity across AI (`app/ai/`), STT (`app/voice/stt.py`), and TTS (`app/voice/tts.py`).
- **Security & Safety First**: Tiered permission system (`SAFE`, `CONFIRMATION_REQUIRED`, `HIGH_RISK`, `BLOCKED`) with zero unapproved shell execution.
- **Web Dashboard**: Lightweight companion dashboard deployable to Vercel.

---

## 🏛️ Architecture & Dataflow

```text
Microphone (On-demand)
       ↓
Lightweight Wake Word
       ↓
Speech-to-Text (STT) [Tamil / Tanglish / English]
       ↓
Conversation Manager & Memory Layer
       ↓
AI Provider (Cloud LLM Inference)
       ↓
Intent & Tool Decision Engine
       ↓
Security & Permission Layer (Confirmation Check)
       ↓
PC Tool Execution (App Control, Browser, Filesystem)
       ↓
Response Generator (Tamil-First Persona)
       ↓
Text-to-Speech (TTS) [Natural Tamil Voice]
       ↓
Speaker Output
```

---

## 📁 Project Structure

```text
myoneAI/
├── app/
│   ├── __init__.py
│   ├── core/                  # Core runtime & lifecycle
│   │   ├── __init__.py
│   │   ├── config.py          # Pydantic settings & env validation
│   │   ├── logging_config.py  # Log rotation & secret redaction
│   │   ├── events.py          # Pub-sub async event bus
│   │   ├── state.py           # State machine & telemetry
│   │   └── main.py            # CLI entrypoint & diagnostic engine
│   ├── voice/                 # Voice pipeline interfaces
│   │   ├── __init__.py
│   │   ├── microphone.py      # Audio capture manager
│   │   ├── wake_word.py       # Wake-word detection interface
│   │   ├── stt.py             # Speech-to-Text abstraction
│   │   ├── tts.py             # Text-to-Speech abstraction
│   │   └── voice_manager.py   # Voice cycle orchestrator
│   ├── ai/                    # Cloud AI & conversation
│   │   ├── __init__.py
│   │   ├── provider.py        # Cloud LLM provider interface
│   │   ├── conversation.py    # Turn & history management
│   │   ├── prompts.py         # Tamil JARVIS persona prompts
│   │   └── memory.py          # Privacy-aware short/long-term memory
│   ├── monitoring/            # On-demand system telemetry
│   │   ├── __init__.py
│   │   ├── system.py          # CPU, RAM, Disk metrics
│   │   ├── battery.py         # Battery & power metrics
│   │   ├── network.py         # Network traffic counters
│   │   └── process.py         # Top process inspector
│   ├── tools/                 # PC control & actions
│   │   ├── __init__.py
│   │   ├── app_control.py     # Application launching / closing
│   │   ├── browser.py         # Web navigation & search
│   │   ├── filesystem.py      # Safe folder/file operations
│   │   ├── system_control.py  # System info & screenshots
│   │   └── media.py           # Volume & media control
│   └── security/              # Access control & confirmations
│       ├── __init__.py
│       ├── permissions.py     # Central permission registry
│       └── confirmations.py   # User prompt verification
├── web/                       # Web dashboard (Phase 11-12)
│   ├── frontend/              # Lightweight dashboard
│   └── api/                   # Vercel serverless functions
├── config/                    # Configuration documentation
│   └── README.md
├── data/                      # Local data directory (.gitkeep)
├── logs/                      # Log directory with rotation (.gitkeep)
├── scripts/                   # Utility scripts (run.bat, test.bat)
├── tests/                     # Comprehensive test suite
├── .env.example               # Configuration template
├── .gitignore                 # Secrets & cache ignore rules
├── requirements.txt           # Minimal lightweight dependencies
├── README.md                  # Project documentation
└── LICENSE                    # MIT License
```

---

## ⚡ Quick Start & Installation

### 1. Prerequisites
- **Python 3.12+**
- **Git**

### 2. Setup Virtual Environment
```powershell
# Clone the repository
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
Configure your `.env` with your API keys (e.g. `AI_API_KEY`, `DEFAULT_LANGUAGE=ta-IN`).

---

## 🧪 Testing & Diagnostics

### Run the Diagnostic Status Command
```powershell
.\scripts\run.bat --status
# Or directly via Python:
python -m app.core.main --status
```

Sample output:
```text
======================================================================
  myoneAI — Tamil JARVIS (v0.1.0)
======================================================================
  [Status]             : [ONLINE] Active
  [State]              : IDLE
  [Uptime]             : 0.0s
  [Process Memory]     : 44.57 MB (Ultra-Lightweight)
----------------------------------------------------------------------
  Hardware Telemetry (i3 / 8GB RAM Optimized):
  [CPU Usage]          : 0.0%
  [RAM Usage]          : 75.2% (5979.5 MB / 7953.7 MB)
  [Battery]            : 100% (Charging)
----------------------------------------------------------------------
  Service Registry:
  [Voice Engine]       : STOPPED
  [Wake Word]          : STOPPED
  [AI Provider]        : gemini (Not Configured)
  [System Monitoring]  : STOPPED
  [Security Layer]     : STOPPED
----------------------------------------------------------------------
  Configuration:
  [Environment]        : development
  [Default Language]   : ta-IN
  [Log File]           : logs/jarvis.log
  [Require Confirm]    : True
======================================================================
```

### Verify Environment
```powershell
python -m app.core.main --check-env
```

### Run Pytest Suite
```powershell
.\scripts\test.bat
# Or:
pytest -v
```

---

## 🗺️ Development Phases

- [x] **Phase 1: Foundation** *(Current)* — Core configuration, rotating logs, event bus, state machine, CLI diagnostics, modular package interfaces, security baseline.
- [ ] **Phase 2: Tamil STT** — Provider integration for pure Tamil & Tamil-English mixed speech.
- [ ] **Phase 3: Tamil TTS** — Natural Tamil voice synthesis.
- [ ] **Phase 4: AI Conversation** — Cloud LLM provider integration with Tamil conversational persona.
- [ ] **Phase 5: Voice Conversation Loop** — Coordinated voice cycle (Idle → Record → STT → AI → TTS → Idle).
- [ ] **Phase 6: Wake Word** — Low-power wake word detection.
- [ ] **Phase 7: Memory** — Privacy-aware short-term and persistent preference memory.
- [ ] **Phase 8: PC Tools** — Whitelisted local PC actions (app launcher, browser, volume).
- [ ] **Phase 9: Permission & Security System** — Tiered permission engine and confirmation prompts.
- [ ] **Phase 10: System Monitoring** — On-demand telemetry reports.
- [ ] **Phase 11: Web Dashboard** — Lightweight frontend dashboard.
- [ ] **Phase 12: Laptop ↔ Vercel Communication** — Secure API sync.
- [ ] **Phase 13: Optimization** — Fine-tuning CPU/RAM profiling and response latency.
- [ ] **Phase 14: Testing** — Comprehensive end-to-end integration tests.
- [ ] **Phase 15: Production Deployment** — Vercel web deployment & local agent service.

---

## 🛡️ Privacy & Security Principles

- **Zero Arbitrary Shell Execution**: The AI cannot run raw shell scripts; only whitelisted tools are allowed.
- **Sensitive Data Redaction**: API keys, passwords, and tokens are automatically scrubbed from all log files.
- **Local Isolation**: Audio is not continuously captured or uploaded.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
