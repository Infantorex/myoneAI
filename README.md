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
  - **Zero Heavy Local LLMs**: Utilizes lightweight Cloud API inference.
  - **No Continuous Background Processing**: Microphone and heavy audio inference activate strictly on demand with Voice Activity Detection (VAD).
  - **Ultra-Low Memory Footprint**: Core runtime consumes **~62.8 MB RAM** on startup.
- **Provider-Independent Interfaces**: Modularity across AI (`app/ai/`), STT (`app/voice/stt.py`), and TTS (`app/voice/tts.py`).
- **Security & Safety First**: Tiered permission system (`SAFE`, `CONFIRMATION_REQUIRED`, `HIGH_RISK`, `BLOCKED`) with zero unapproved shell execution.
- **Web Dashboard**: Lightweight companion dashboard deployable to Vercel.

---

## 🎙️ Speech-to-Text (STT) Subsystem (Phase 2)

### Architecture
```text
Microphone (On-demand)
       ↓
sounddevice Audio Capture (16kHz Mono 16-bit PCM)
       ↓
Energy-Based Voice Activity Detection (VAD)
  - Pre-speech rolling buffer
  - Dynamic ambient noise calibration
  - Auto-detection of speech end (1.5s silence)
       ↓
In-Memory WAV Packaging (Zero disk thrashing)
       ↓
STT Provider Abstraction (app/voice/stt.py)
  ├── GoogleSTTProvider (Default, cloud web speech, 0 MB weights)
  ├── GroqWhisperSTTProvider (Cloud Whisper API)
  └── MockSTTProvider (Offline / CI/CD testing)
       ↓
Recognized Tamil / English / Mixed Text Output
```

### Supported Languages & Dialects
- **Pure Tamil (`ta-IN`)**: e.g., `"ஜார்விஸ், இன்று என்ன செய்ய வேண்டும்?"`
- **Tamil-English Mixed / Code-switching**: e.g., `"Open Chrome பண்ணு"`, `"என் project folder open பண்ணு"`
- **English (`en-IN`, `en-US`)**: e.g., `"What is my battery percentage?"`

---

## 📁 Project Structure

```text
myoneAI/
├── app/
│   ├── __init__.py                         # Version and metadata
│   ├── core/                               # Core runtime & lifecycle
│   │   ├── __init__.py
│   │   ├── config.py                       # Pydantic BaseSettings, env validation
│   │   ├── logging_config.py               # Rotating log handler & credential redactor
│   │   ├── events.py                       # Pub-sub async event bus
│   │   ├── state.py                        # State machine & telemetry
│   │   └── main.py                         # CLI entrypoint & diagnostic engine
│   ├── voice/                              # Voice & STT subsystem
│   │   ├── __init__.py
│   │   ├── audio_config.py                 # Centralized audio parameters & VAD thresholds
│   │   ├── exceptions.py                   # Structured Voice & STT exceptions
│   │   ├── vad.py                          # Energy-based Voice Activity Detection
│   │   ├── microphone.py                   # Sounddevice audio capture manager
│   │   ├── stt.py                          # Provider-independent STT interfaces
│   │   ├── tts.py                          # Text-to-Speech abstraction
│   │   ├── voice_manager.py                # Voice pipeline coordinator
│   │   ├── wake_word.py                    # Wake-word detection interface
│   │   ├── test_microphone.py              # Mode 1: Microphone hardware diagnostic
│   │   └── test_stt.py                     # Mode 2 & 3: Live mic & file-based STT test
│   ├── ai/                                 # AI & reasoning layer
│   │   ├── __init__.py
│   │   ├── provider.py                     # Cloud LLM provider interface
│   │   ├── conversation.py                 # Dialogue turn manager & context trimmer
│   │   ├── prompts.py                      # Tamil JARVIS persona prompts
│   │   └── memory.py                       # Privacy-aware short/long-term memory
│   ├── monitoring/                         # On-demand system telemetry
│   ├── tools/                              # PC control & actions
│   └── security/                           # Access control & confirmations
├── docs/
│   └── phase2-performance.md               # Hardware benchmarks on i3 / 8GB RAM
├── security/
│   └── phase2-stt-audit.md                 # Security & privacy audit checklist
├── scripts/
│   ├── run.bat                             # Windows launcher script
│   └── test.bat                            # Pytest runner script
├── tests/                                  # 47 automated unit tests (0 failed)
├── .env.example                            # Configuration template
├── .gitignore                              # Secrets & cache ignore rules
├── pytest.ini                              # Pytest configuration
├── requirements.txt                        # Lightweight dependencies
└── README.md
```

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

---

## 🧪 Testing Voice & STT Subsystems

### Mode 1 — Microphone Hardware Diagnostic
Scans available audio inputs and tests a live 2-second capture burst with an ASCII volume meter:
```powershell
python -m app.voice.test_microphone
```

### Mode 2 — Live Speech-to-Text Test (Tamil)
Records one spoken utterance using automatic VAD silence detection and transcribes it:
```powershell
python -m app.voice.test_stt
```

### Mode 3 — File-Based STT Test
Transcribe from an existing WAV audio file without using a microphone:
```powershell
python -m app.voice.test_stt --file sample_tamil.wav
# Or with mock provider:
python -m app.voice.test_stt --file sample_tamil.wav --provider mock
```

### Run Diagnostic Status Command
```powershell
.\scripts\run.bat --status
```

### Run Automated Unit Tests (47 tests)
```powershell
.\scripts\test.bat
# Or:
pytest -v
```

---

## 📊 Phase 2 Benchmark Results

| Metric | Measured Value | Threshold | Status |
| :--- | :--- | :--- | :--- |
| **Startup RAM** | **62.8 MB** | < 100 MB | 🟢 Ultra-Lightweight |
| **Active Capture & VAD RAM** | **63.1 MB** | < 120 MB | 🟢 Zero Leak |
| **VAD Processing Latency** | **0.47 ms / 1s audio** | < 10.0 ms | 🟢 Real-time (<0.1% CPU) |
| **Local Model Weight Size** | **0 MB (Cloud API)** | 0 MB | 🟢 Cloud Optimized |
| **Unit Test Pass Rate** | **47 / 47 (100%)** | 100% | 🟢 All Pass (0 failed) |

---

## 🛡️ Privacy & Security Principles

- **Zero Permanent Audio Retention**: Audio is captured into in-memory buffers and discarded immediately after transcription.
- **No Continuous Audio Streaming**: Microphone activates strictly on demand.
- **Secret Redaction**: API keys and authorization tokens are masked in all logs.

---

## 🗺️ Development Roadmap

- [x] **Phase 1: Foundation** — Core config, logging, event bus, state machine, CLI diagnostics.
- [x] **Phase 2: Tamil STT** — Audio capture, VAD, Google/Groq STT providers, Mode 1/2/3 tests, performance benchmarks, security audit.
- [ ] **Phase 3: Tamil TTS** — Natural Tamil voice synthesis.
- [ ] **Phase 4: AI Conversation** — Cloud LLM provider integration with Tamil conversational persona.
- [ ] **Phase 5: Voice Conversation Loop** — Coordinated voice cycle (Idle → Record → STT → AI → TTS → Idle).
- [ ] **Phase 6: Wake Word** — Low-power wake word detection.
- [ ] **Phase 7: Memory** — Privacy-aware short-term and persistent preference memory.
- [ ] **Phase 8: PC Tools** — Whitelisted local PC actions.
- [ ] **Phase 9: Permission & Security System** — Tiered permission engine.
- [ ] **Phase 10: System Monitoring** — On-demand telemetry reports.
- [ ] **Phase 11: Web Dashboard** — Lightweight frontend dashboard.
- [ ] **Phase 12: Laptop ↔ Vercel Communication** — Secure API sync.
- [ ] **Phase 13: Optimization** — Fine-tuning CPU/RAM profiling.
- [ ] **Phase 14: Testing** — End-to-end integration tests.
- [ ] **Phase 15: Production Deployment** — Vercel web deployment & local agent service.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
