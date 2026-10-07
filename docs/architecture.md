# System Architecture — myoneAI (v1.0.0)

**myoneAI — Tamil JARVIS** is engineered as a modular, asynchronous, local-first system optimized for Windows laptops with 8 GB RAM and 10th Gen Intel Core i3 processors.

---

## 1. High-Level Architectural Diagram

```text
                    ┌────────────────────────┐
                    │      Vercel Cloud      │
                    │   Dashboard / API      │
                    └───────────┬────────────┘
                                │
                          HTTPS / WSS
                                │
                                ▼
┌────────────────────────────────────────────────────────────┐
│                    WINDOWS LAPTOP RUNTIME                  │
│                                                            │
│   ┌──────────────┐      ┌─────────────┐     ┌───────────┐  │
│   │  Wake Word   │ ───► │  Tamil STT  │ ──► │  AI Core  │  │
│   │   Detector   │      │ (Cloud API) │     │  Engine   │  │
│   └──────────────┘      └─────────────┘     └─────┬─────┘  │
│                                                   │        │
│                                                   ▼        │
│  ┌──────────────┐       ┌─────────────┐     ┌───────────┐  │
│  │   Speaker    │ ◄───  │  Tamil TTS  │ ◄── │  Memory & │  │
│  │  (miniaudio) │       │ (Neural HD) │     │  Tools    │  │
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

## 2. Core Subsystems

1. **Voice Pipeline (`app/voice/`)**:
   - `WakeWord`: Continuous local energy/acoustic detection (< 0.5% CPU load).
   - `VAD`: Vectorized RMS energy speech start/end boundary detector.
   - `STT`: Cloud transcription client for Tamil, English, and Tanglish.
   - `TTS`: In-memory streaming neural speech synthesis.
2. **AI Engine (`app/ai/`)**:
   - `ConversationManager`: 12-turn FIFO bounded history, Tamil JARVIS persona prompt, and short-term reasoning.
3. **Memory Subsystem (`app/core/memory/`)**:
   - `SQLiteMemoryStore`: WAL-mode persistence for user facts and preferences.
   - `MemoryRetriever`: Keyword and token overlap relevance scorer.
   - `PrivacyFilter`: Rejects credentials, passwords, and financial data.
4. **PC Tools & Permissions (`app/tools/`, `app/security/`)**:
   - `PermissionManager`: Central enforcement of SAFE, CONFIRMATION_REQUIRED, and BLOCKED tiers.
   - `ToolRegistry`: Statically declared executable capabilities.
5. **Productivity (`app/productivity/`)**:
   - Tasks, natural-language datetime reminders, recurring schedules, and in-memory async countdown timers.
6. **Local Dashboard (`web/`)**:
   - FastAPI server (`127.0.0.1:8000`) with dark-mode web interface and REST API.
7. **Cloud Bridge (`app/cloud/`)**:
   - HMAC-SHA256 authenticated outbound bridge to Vercel with replay defense and offline queuing.
