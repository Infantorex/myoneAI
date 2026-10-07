# myoneAI — Tamil JARVIS 🎙️🤖

[![Python 3.12](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Modular%20%26%20Async-brightgreen.svg)]()
[![Hardware Optimization](https://img.shields.io/badge/Target-8GB%20RAM%20%7C%20Intel%20i3-orange.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **myoneAI** is an ultra-lightweight, resource-efficient personal AI assistant and Tamil companion (Tamil JARVIS) designed specifically for personal laptops with strict hardware constraints (8 GB RAM, Intel Core i3 10th Gen, Windows).

---

## 🚀 Key Capabilities

- **Lightweight Wake Word System (Phase 6)**: Hands-free activation via "JARVIS" wake phrase with low-power local acoustic/energy evaluation (< 0.5% idle CPU), debounced cooldown protection, and seamless microphone ownership handover.
- **Natural Voice Conversation Loop (Phase 5)**: Complete end-to-end conversational pipeline connecting Microphone → Speech Detection (VAD) → Tamil STT → AI Conversation Engine → Tamil TTS → Speaker playback.
- **AI Brain & Natural Conversation (Phase 4)**: Context-aware conversational intelligence supporting pure Tamil (`ta-IN`), English, and mixed Tanglish code-switching with concise, friendly JARVIS persona.
- **Tamil Speech Recognition (STT)**: Fast cloud transcription for Tamil, English, and Tanglish with on-demand Voice Activity Detection (VAD).
- **Natural Tamil Voice Synthesis (TTS)**: High-definition neural speech (`ta-IN-PallaviNeural`, `ta-IN-ValluvarNeural`) with 100% in-memory audio streaming.
- **Hardware-First Resource Efficiency**:
  - **Zero Continuous Cloud Audio Upload**: Background wake listening evaluates audio locally without streaming ambient sound to cloud APIs.
  - **Zero Heavy Local LLMs**: Utilizes lightweight Cloud API inference (Gemini / OpenAI REST).
  - **Ultra-Low Memory Footprint**: Baseline memory footprint is **~72.0 MB RAM** with zero background polling.
  - **Bounded Short-Term Context**: Strict FIFO history management (`AI_MAX_HISTORY_MESSAGES=12`) prevents memory and token bloat.
  - **100% In-Memory Audio**: Audio buffers are processed purely in volatile RAM, eliminating temporary files and disk wear.
- **Provider-Independent Interfaces**: Clean abstractions across Wake Word (`app/voice/wakeword_provider.py`), AI (`app/ai/provider.py`), STT (`app/voice/stt.py`), and TTS (`app/voice/tts.py`).
- **Safety & Truth Boundaries**: Enforces **No-Fake-Actions** rule — the assistant will never claim to perform actions it has not executed.

> [!NOTE]
> Wake-word detection is optional and can be disabled via `WAKE_WORD_ENABLED=false`. Manual voice mode remains available as a fallback via `python -m app.voice.conversation`.

---

## 🏛️ System Architecture

```text
Idle State
    ↓
Low-Power Wake Word Listener (Local Energy & Keyword Matching)
    ↓
"JARVIS" Detected (< 15 ms latency)
    ↓
Microphone Stream Paused & Handed Over
    ↓
Optional Short Wake Response ("சொல்லுங்க.")
    ↓
Speech Detection & VAD (0.47 ms energy check)
    ↓
Tamil STT Provider (Google / Groq Whisper)
    ↓
Conversation Manager (Bounded 12-turn FIFO Context)
    ↓
AI Provider (Gemini / OpenAI / Groq)
    ↓
Tamil TTS Manager (Microsoft Edge Neural `ta-IN-PallaviNeural`)
    ↓
In-Memory Audio Decoder & Player (miniaudio / sounddevice)
    ↓
Speaker Output
    ↓
Wake Listener Resumes & Returns to Idle
```

### State Machine Lifecycle
```text
  IDLE ───> WAKE_LISTENING ───> WAKE_DETECTED ───> ACTIVATING ───> LISTENING ───> THINKING ───> SPEAKING ───> IDLE
   ▲                                                                                                           │
   └─────────────────────────────────── [ERROR / CANCEL] ──────────────────────────────────────────────────────┘
```

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
│   ├── ai/                                 # AI Conversation Engine (Phase 4)
│   │   ├── __init__.py
│   │   ├── errors.py                       # Structured AI & provider exceptions
│   │   ├── manager.py                      # Conversation context manager & FIFO trimmer
│   │   ├── models.py                       # ChatMessage, AIRequestConfig, AIResponse schemas
│   │   ├── prompts.py                      # JARVIS Tamil persona & No-Fake-Actions rules
│   │   ├── provider.py                     # Provider abstraction (Gemini, OpenAI, Mock)
│   │   └── test_ai.py                      # Interactive & CLI chat test utility
│   ├── voice/                              # Voice, STT, TTS, Wake Word & Conversation Loop
│   │   ├── __init__.py
│   │   ├── audio.py                        # In-memory audio player & speaker output
│   │   ├── audio_config.py                 # Centralized audio parameters & VAD thresholds
│   │   ├── conversation.py                 # VoiceConversationManager & state machine (Phase 5)
│   │   ├── exceptions.py                   # Structured Voice, STT, TTS & Wake exceptions
│   │   ├── jarvis.py                       # Main Hands-Free Assistant Entrypoint (Phase 6)
│   │   ├── microphone.py                   # Sounddevice audio capture manager
│   │   ├── stt.py                          # Provider-independent STT interfaces
│   │   ├── tts.py                          # Provider-independent TTS & TTSManager
│   │   ├── vad.py                          # Energy-based Voice Activity Detection
│   │   ├── voice_manager.py                # Voice pipeline coordinator
│   │   ├── wakeword.py                     # Unified wake word exports (Phase 6)
│   │   ├── wakeword_manager.py             # WakeWordManager & mic ownership handover
│   │   ├── wakeword_provider.py            # Wake word provider abstraction & local engine
│   │   ├── test_wakeword.py                # Wake word test runner (Phase 6)
│   │   ├── test_voice_loop.py              # Voice loop test runner (Phase 5)
│   │   ├── test_microphone.py              # Mode 1: Microphone hardware diagnostic
│   │   ├── test_stt.py                     # Mode 2 & 3: Live mic & file-based STT test
│   │   └── test_tts.py                     # Interactive & CLI Text-to-Speech test
│   ├── monitoring/                         # On-demand system telemetry
│   ├── tools/                              # PC control & actions
│   └── security/                           # Access control & confirmations
├── docs/
│   ├── phase2-performance.md               # STT hardware benchmarks
│   ├── phase3-performance.md               # TTS hardware benchmarks
│   ├── phase4-performance.md               # AI Conversation benchmarks
│   ├── phase4-privacy.md                   # AI privacy & data transmission details
│   ├── phase5-performance.md               # Voice conversation loop benchmarks
│   ├── phase5-privacy.md                   # Voice privacy & audio lifecycle details
│   ├── phase6-performance.md               # Wake word system benchmarks
│   └── phase6-privacy.md                   # Wake word privacy & audio lifecycle details
├── security/
│   ├── phase2-stt-audit.md                 # STT security audit checklist
│   ├── phase3-tts-audit.md                 # TTS security audit checklist
│   ├── phase4-ai-audit.md                  # AI Conversation security audit checklist
│   ├── phase5-voice-loop-audit.md          # Voice loop security audit checklist
│   └── phase6-wakeword-audit.md            # Wake word security audit checklist
├── scripts/
│   ├── run.bat                             # Windows launcher script
│   └── test.bat                            # Pytest runner script
├── tests/                                  # 96 automated unit/integration tests (0 failed)
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
Add your API key (e.g. `AI_API_KEY=your_gemini_api_key_here`).

---

## 🤖 Hands-Free JARVIS Usage (Phase 6)

### Main Hands-Free Assistant
Listens continuously for "JARVIS", provides a short acknowledgement ("சொல்லுங்க."), and flows seamlessly into Tamil conversation:
```powershell
# Live assistant with microphone:
python -m app.voice.jarvis

# Offline mock simulation without hardware:
python -m app.voice.jarvis --mock
```

### Wake Word Detection Diagnostic
Test wake phrase detection independently:
```powershell
# Live wake word test:
python -m app.voice.test_wakeword

# Offline mock test:
python -m app.voice.test_wakeword --mock
```

---

## 🎙️ Voice & AI Subsystem Tests

### One-Shot & Interactive Voice Loop (Phase 5)
```powershell
# One-shot voice turn:
python -m app.voice.conversation

# Continuous interactive mode:
python -m app.voice.conversation --interactive
```

### AI Conversation CLI Test (Phase 4)
```powershell
python -m app.ai.test_ai
```

### Text-to-Speech (TTS) CLI Test (Phase 3)
```powershell
python -m app.voice.test_tts --text "வணக்கம் Infanto, எப்படி இருக்கிறீர்கள்?"
```

### Speech-to-Text (STT) CLI Test (Phase 2)
```powershell
python -m app.voice.test_stt
```

### Run All Automated Unit Tests (96 tests)
```powershell
.\scripts\test.bat
# Or:
pytest -v
```

---

## 📊 Performance Benchmarks (Phase 6)

| Subsystem | Metric | Measured Value | Threshold | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **System** | **Startup RAM** | **72.0 MB** | < 100 MB | 🟢 Ultra-Lightweight |
| **Wake Listener** | **Idle Wake Listening RAM** | **72.0 MB** | < 100 MB | 🟢 Zero Leak |
| **Wake Listener** | **Idle Wake CPU** | **< 0.5% CPU** | < 3.0% CPU | 🟢 Power Efficient |
| **Wake Listener** | **Wake Trigger Latency** | **12.14 ms** | < 100 ms | 🟢 Real-time Trigger |
| **Voice Loop** | **Active Turn RAM Overhead** | **+2.90 MB RAM** | < 50 MB | 🟢 Zero Leak |
| **Speech VAD** | **VAD Chunk Processing Time** | **0.47 ms / 1s audio** | < 10 ms | 🟢 Real-time (<0.1% CPU) |
| **Local Models**| **Local Model Weight Size** | **0 MB (Cloud APIs)** | 0 MB | 🟢 Cloud Optimized |
| **Continuous Upload** | **Background Cloud Stream**| **0 Bytes / sec** | 0 cloud stream | 🟢 100% Local Wake Engine |
| **Disk I/O** | **Temporary Audio Files** | **0 Bytes (RAM only)** | 0 disk writes | 🟢 Zero SSD Thrashing |
| **Tests** | **Unit & Integration Test Pass Rate** | **96 / 96 (100%)** | 100% | 🟢 All Pass (0 failed) |

---

## 🗺️ Development Roadmap

- [x] **Phase 1: Foundation** — Core config, logging, event bus, state machine, CLI diagnostics.
- [x] **Phase 2: Tamil STT** — Audio capture, VAD, Google/Groq STT providers, Mode 1/2/3 tests.
- [x] **Phase 3: Tamil TTS** — Microsoft Edge Neural TTS (`ta-IN-PallaviNeural`), in-memory audio player, overlap protection.
- [x] **Phase 4: AI Conversation** — Cloud LLM provider abstraction (Gemini / OpenAI), JARVIS Tamil persona, short-term context window, safety boundaries.
- [x] **Phase 5: Voice Conversation Loop** — Coordinated voice cycle (Idle → Record → STT → AI → TTS → Idle), interactive mode, mock simulation, and interrupt safety.
- [x] **Phase 6: Wake Word** — Low-power local wake word detection, debouncing cooldown, microphone ownership handover, and hands-free JARVIS runtime.
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
