# myoneAI — Tamil JARVIS 🎙️🤖

[![Python 3.12](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Modular%20%26%20Async-brightgreen.svg)]()
[![Hardware Optimization](https://img.shields.io/badge/Target-8GB%20RAM%20%7C%20Intel%20i3-orange.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **myoneAI** is an ultra-lightweight, resource-efficient personal AI assistant and Tamil companion (Tamil JARVIS) designed specifically for personal laptops with strict hardware constraints (8 GB RAM, Intel Core i3 10th Gen, Windows).

---

## 🚀 Key Capabilities

- **Tamil Speech Recognition (STT)**: Fast cloud transcription for pure Tamil (`ta-IN`), English, and mixed Tanglish code-switching with on-demand Voice Activity Detection (VAD).
- **Natural Tamil Voice Synthesis (TTS)**: High-definition neural speech (`ta-IN-PallaviNeural`, `ta-IN-ValluvarNeural`) powered by Microsoft Edge Neural TTS with 100% in-memory audio streaming.
- **Hardware-First Resource Efficiency**:
  - **Zero Heavy Local Models**: All AI, STT, and TTS inference use lightweight cloud APIs.
  - **Ultra-Low Memory Footprint**: Startup memory footprint is **~72.4 MB RAM** with zero GPU requirements.
  - **100% In-Memory Audio I/O**: Zero disk wear or temporary audio files created.
- **Provider-Independent Interfaces**: Clean abstractions across AI (`app/ai/`), STT (`app/voice/stt.py`), and TTS (`app/voice/tts.py`).
- **Security & Safety First**: Tiered permission system (`SAFE`, `CONFIRMATION_REQUIRED`, `HIGH_RISK`, `BLOCKED`) with secret redaction in all logs.

---

## 🏛️ Voice Subsystems Architecture

```text
Speech Input (STT)                      Speech Output (TTS)
------------------                      -------------------
Microphone (On-demand)                  Text Input (Tamil / English / Mixed)
       ↓                                       ↓
sounddevice Audio Capture (16kHz PCM)   TTS Manager (Sanitization & Overlap Lock)
       ↓                                       ↓
Energy-based VAD (0.47 ms latency)      TTS Provider Abstraction (app/voice/tts.py)
       ↓                                  ├── EdgeTTSProvider (ta-IN-PallaviNeural, 0 MB weights)
STT Provider (Google / Groq / Mock)       └── MockTTSProvider (Offline CI/CD testing)
       ↓                                       ↓
Recognized Text                         In-Memory MP3/WAV Audio Decoding (miniaudio)
                                               ↓
                                        Audio Player & Speaker Output (sounddevice)
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
│   ├── voice/                              # Voice, STT, & TTS subsystem
│   │   ├── __init__.py
│   │   ├── audio.py                        # In-memory audio player & speaker output
│   │   ├── audio_config.py                 # Centralized audio parameters & VAD thresholds
│   │   ├── exceptions.py                   # Structured Voice, STT & TTS exceptions
│   │   ├── microphone.py                   # Sounddevice audio capture manager
│   │   ├── stt.py                          # Provider-independent STT interfaces
│   │   ├── tts.py                          # Provider-independent TTS & TTSManager
│   │   ├── vad.py                          # Energy-based Voice Activity Detection
│   │   ├── voice_manager.py                # Voice pipeline coordinator
│   │   ├── wake_word.py                    # Wake-word detection interface
│   │   ├── test_microphone.py              # Mode 1: Microphone hardware diagnostic
│   │   ├── test_stt.py                     # Mode 2 & 3: Live mic & file-based STT test
│   │   └── test_tts.py                     # Interactive & CLI Text-to-Speech test
│   ├── ai/                                 # AI & reasoning layer
│   ├── monitoring/                         # On-demand system telemetry
│   ├── tools/                              # PC control & actions
│   └── security/                           # Access control & confirmations
├── docs/
│   ├── phase2-performance.md               # STT hardware benchmarks
│   └── phase3-performance.md               # TTS hardware benchmarks
├── security/
│   ├── phase2-stt-audit.md                 # STT security audit checklist
│   └── phase3-tts-audit.md                 # TTS security audit checklist
├── scripts/
│   ├── run.bat                             # Windows launcher script
│   └── test.bat                            # Pytest runner script
├── tests/                                  # 62 automated unit tests (0 failed)
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

## 🧪 Testing Voice Subsystems (STT & TTS)

### Text-to-Speech (TTS) CLI Tests
```powershell
# Interactive mode (prompts for Tamil / English text):
python -m app.voice.test_tts

# Direct Tamil speech test:
python -m app.voice.test_tts --text "வணக்கம் Infanto, எப்படி இருக்கிறீர்கள்?"

# Mixed Tamil-English speech test:
python -m app.voice.test_tts --text "வணக்கம் Infanto, இன்று Python project work பண்ணலாமா?"

# English speech test:
python -m app.voice.test_tts --language en-US --text "Hello Infanto, system is online."

# Offline Mock test:
python -m app.voice.test_tts --provider mock --text "Mock speech test"
```

### Speech-to-Text (STT) CLI Tests
```powershell
# Mode 1: Microphone hardware diagnostic
python -m app.voice.test_microphone

# Mode 2: Live single-utterance speech recognition
python -m app.voice.test_stt

# Mode 3: File-based speech recognition
python -m app.voice.test_stt --file sample_tamil.wav
```

### Run System Health Diagnostic
```powershell
.\scripts\run.bat --status
```

### Run Automated Unit Tests (62 tests)
```powershell
.\scripts\test.bat
# Or:
pytest -v
```

---

## 📊 Performance Benchmarks (Phase 3)

| Subsystem | Metric | Measured Value | Threshold | Status |
| :--- | :--- | :--- | :--- | :--- |
| **System** | **Startup RAM** | **72.4 MB** | < 100 MB | 🟢 Ultra-Lightweight |
| **System** | **Idle CPU** | **0.0%** | < 1% | 🟢 Zero Idle Drain |
| **TTS** | **Memory Overhead** | **+1.2 MB during synthesis** | < 20 MB | 🟢 Negligible |
| **TTS** | **Edge-TTS Latency** | **~1.0s - 1.5s** | < 3.0s | 🟢 High-speed Stream |
| **TTS** | **Disk I/O** | **0 Bytes (100% In-Memory)** | 0 bytes | 🟢 Zero Disk Wear |
| **Tests** | **Unit Test Pass Rate** | **62 / 62 (100%)** | 100% | 🟢 All Pass (0 failed) |

---

## 🗺️ Development Roadmap

- [x] **Phase 1: Foundation** — Core config, logging, event bus, state machine, CLI diagnostics.
- [x] **Phase 2: Tamil STT** — Audio capture, VAD, Google/Groq STT providers, Mode 1/2/3 tests.
- [x] **Phase 3: Tamil TTS** — Microsoft Edge Neural TTS (`ta-IN-PallaviNeural`), in-memory audio player, overlap protection, CLI tests.
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
