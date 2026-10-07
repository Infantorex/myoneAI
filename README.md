# myoneAI — Tamil JARVIS 🎙️🤖

[![Python 3.12](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Modular%20%26%20Async-brightgreen.svg)]()
[![Hardware Optimization](https://img.shields.io/badge/Target-8GB%20RAM%20%7C%20Intel%20i3-orange.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **myoneAI** is an ultra-lightweight, resource-efficient personal AI assistant and Tamil companion (Tamil JARVIS) designed specifically for personal laptops with strict hardware constraints (8 GB RAM, Intel Core i3 10th Gen, Windows).

---

## 🚀 Key Capabilities

- **Controlled AI Memory (Phase 7)**: Persistent, privacy-aware SQLite memory storing user preferences, project facts, and context across sessions with natural language memory commands ("Remember that...", "What do you remember about me?", "Forget that...") and automated sensitive-credential blocking.
- **Lightweight Wake Word System (Phase 6)**: Hands-free activation via "JARVIS" wake phrase with low-power local acoustic/energy evaluation (< 0.5% idle CPU), debounced cooldown protection, and seamless microphone ownership handover.
- **Natural Voice Conversation Loop (Phase 5)**: Complete end-to-end conversational pipeline connecting Microphone → Speech Detection (VAD) → Tamil STT → AI Conversation Engine → Tamil TTS → Speaker playback.
- **AI Brain & Natural Conversation (Phase 4)**: Context-aware conversational intelligence supporting pure Tamil (`ta-IN`), English, and mixed Tanglish code-switching with concise, friendly JARVIS persona.
- **Tamil Speech Recognition (STT)**: Fast cloud transcription for Tamil, English, and Tanglish with on-demand Voice Activity Detection (VAD).
- **Natural Tamil Voice Synthesis (TTS)**: High-definition neural speech (`ta-IN-PallaviNeural`, `ta-IN-ValluvarNeural`) with 100% in-memory audio streaming.
- **Hardware-First Resource Efficiency**:
  - **Zero Heavy Local LLMs / Vector DBs**: Pure SQLite local store + Cloud API inference.
  - **Zero Continuous Cloud Audio Upload**: Background wake listening evaluates audio locally without streaming ambient sound to cloud APIs.
  - **Ultra-Low Memory Footprint**: Baseline memory footprint is **~46.4 MB RAM** with zero background polling.
  - **Bounded Memory Context**: Hard cap of `MEMORY_MAX_RESULTS=5` and `MEMORY_MAX_CONTEXT_CHARS=3000` prevents token bloat.
  - **100% In-Memory Audio**: Audio buffers are processed purely in volatile RAM, eliminating temporary files and disk wear.
- **Safety & Truth Boundaries**: Enforces **No-Fake-Actions** rule — the assistant will never claim to perform actions it has not executed.

> [!NOTE]
> myoneAI does not permanently store every conversation. Only approved/useful memories are stored. Memory can be disabled via `MEMORY_ENABLED=false`.

---

## 🏛️ System Architecture

```text
User Speech / Text
       ↓
Wake Word Detector ("JARVIS")
       ↓
Memory Intent / Privacy Filter (Rejects Passwords/Tokens)
       ↓
SQLite Memory Store (`data/memory.db`)
       ↓
Token Relevance Retriever (Top 5 Contextual Memories)
       ↓
AI Conversation Manager (Persona + Relevant Memory Context)
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
│   │   ├── config.py                       # Pydantic BaseSettings, env validation
│   │   ├── logging_config.py               # Rotating log handler & credential redactor
│   │   ├── events.py                       # Pub-sub async event bus
│   │   ├── state.py                        # State machine & telemetry
│   │   ├── main.py                         # CLI entrypoint & diagnostic engine
│   │   └── memory/                         # Controlled AI Memory System (Phase 7)
│   │       ├── __init__.py
│   │       ├── models.py                   # MemoryItem, MemoryCategory, MemorySource
│   │       ├── privacy.py                  # Sensitive credential filter & regex rejection
│   │       ├── store.py                    # SQLite persistence engine & upsert
│   │       ├── retrieval.py                # Bounded keyword & token relevance scoring
│   │       ├── manager.py                  # MemoryManager & natural command parser
│   │       └── test_memory.py              # Interactive & automated CLI test utility
│   ├── ai/                                 # AI Conversation Engine (Phase 4)
│   │   ├── __init__.py
│   │   ├── errors.py                       # Structured AI & provider exceptions
│   │   ├── manager.py                      # Conversation manager & memory context injector
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
│   ├── phase6-privacy.md                   # Wake word privacy & audio lifecycle details
│   ├── phase7-performance.md               # AI Memory benchmarks & latency
│   └── phase7-privacy.md                   # AI Memory privacy & credential policies
├── security/
│   ├── phase2-stt-audit.md                 # STT security audit checklist
│   ├── phase3-tts-audit.md                 # TTS security audit checklist
│   ├── phase4-ai-audit.md                  # AI Conversation security audit checklist
│   ├── phase5-voice-loop-audit.md          # Voice loop security audit checklist
│   ├── phase6-wakeword-audit.md            # Wake word security audit checklist
│   └── phase7-memory-audit.md              # AI Memory security audit checklist
├── scripts/
│   ├── run.bat                             # Windows launcher script
│   └── test.bat                            # Pytest runner script
├── tests/                                  # 106 automated unit/integration tests (0 failed)
├── .env.example                            # Configuration template
├── .gitignore                              # Secrets, SQLite databases & cache ignore rules
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

## 🧠 Controlled AI Memory Commands (Phase 7)

### Natural Memory Interactions
- **Remembering Facts**:
  - *"Remember that my project is called Vibrawave"*
  - *"Remember that I prefer Tamil responses"*
  - *"எனக்கு தமிழ் பிடிக்கும் நினைவில் வைத்துக்கொள்"*
- **Inspecting Saved Memories**:
  - *"What do you remember about me?"*
  - *"என்னை பற்றி என்ன நினைவிருக்கிறது?"*
- **Deleting Memories**:
  - *"Forget that my project is Vibrawave"*
  - *"Forget my project information"*
- **Clearing All Memories**:
  - *"Clear all memories"* → Requires explicit confirmation (*"Yes, clear memories"*).

### Memory CLI Management Tool
```powershell
# Interactive memory management:
python -m app.core.memory.test_memory

# Automated verification demo:
python -m app.core.memory.test_memory --demo
```

---

## 🤖 Hands-Free JARVIS Usage (Phase 6)

### Main Hands-Free Assistant
```powershell
# Live assistant with microphone:
python -m app.voice.jarvis

# Offline mock simulation without hardware:
python -m app.voice.jarvis --mock
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

### Run All Automated Unit Tests (106 tests)
```powershell
.\scripts\test.bat
# Or:
pytest -v
```

---

## 📊 Performance Benchmarks (Phase 7)

| Subsystem | Metric | Measured Value | Threshold | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **System** | **Startup RAM** | **46.4 MB** | < 100 MB | 🟢 Ultra-Lightweight |
| **Memory Store**| **Database Init Time** | **16.83 ms** | < 100 ms | 🟢 Near-instant SQLite |
| **Memory Store**| **Average Insertion Latency** | **7.85 ms** | < 50 ms | 🟢 Real-time Write |
| **Memory Store**| **Average Search Latency** | **1.17 ms** | < 20 ms | 🟢 Fast Index Lookup |
| **Memory Store**| **Context Retrieval Latency** | **1.50 ms** | < 20 ms | 🟢 Real-time Ranking |
| **Memory Store**| **50 Items DB Size on Disk** | **32.0 KB** | < 1.0 MB | 🟢 Negligible Storage |
| **Prompt Limit**| **Max Memory Prompt Context** | **<= 3,000 chars** | < 4,000 chars | 🟢 Token Bound Enforced |
| **Tests** | **Unit & Integration Test Pass Rate** | **106 / 106 (100%)**| 100% | 🟢 All Pass (0 failed) |

---

## 🗺️ Development Roadmap

- [x] **Phase 1: Foundation** — Core config, logging, event bus, state machine, CLI diagnostics.
- [x] **Phase 2: Tamil STT** — Audio capture, VAD, Google/Groq STT providers, Mode 1/2/3 tests.
- [x] **Phase 3: Tamil TTS** — Microsoft Edge Neural TTS (`ta-IN-PallaviNeural`), in-memory audio player, overlap protection.
- [x] **Phase 4: AI Conversation** — Cloud LLM provider abstraction (Gemini / OpenAI), JARVIS Tamil persona, short-term context window, safety boundaries.
- [x] **Phase 5: Voice Conversation Loop** — Coordinated voice cycle (Idle → Record → STT → AI → TTS → Idle), interactive mode, mock simulation, and interrupt safety.
- [x] **Phase 6: Wake Word** — Low-power local wake word detection, debouncing cooldown, microphone ownership handover, and hands-free JARVIS runtime.
- [x] **Phase 7: Memory** — Controlled AI memory, SQLite persistence, relevance retrieval, privacy filter, natural memory commands.
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
