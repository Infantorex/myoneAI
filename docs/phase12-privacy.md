# Phase 12 — Secure Laptop ↔ Vercel Communication Privacy Policy

## 1. Information Transmitted to Cloud

The following **safe telemetry and synchronization data** may be transmitted to the Cloud Control Plane:
- Online / Offline heartbeat status
- Assistant execution state (`idle`, `listening`, `thinking`, `speaking`, `error`)
- Lightweight hardware telemetry (CPU %, RAM %, Disk %, Battery %)
- Device identity (`device_id`, `device_name`, `device_version`, `platform_os`)
- Active tasks / reminders metadata (for dashboard visualization)
- Timestamp and execution outcome of user-approved safe tools

---

## 2. Information NEVER Transmitted to Cloud

The following items are **strictly prohibited** from leaving the Windows laptop:
- ❌ **Raw audio files and microphone recordings**
- ❌ **AI, STT, and TTS cloud API keys**
- ❌ **Local authentication tokens and passwords**
- ❌ **Desktop screenshots and webcam feeds**
- ❌ **Private files and browser cookies**
- ❌ **SQLite memory database and raw SQL records**

---

## 3. Offline Safety & User Control

- **Cloud Communication is Optional:** Controlled by `CLOUD_ENABLED=false` by default in `.env`.
- **Zero Background Cloud Audio Upload:** Audio processing (VAD, wake word, transcription) happens locally or directly with designated STT providers, never through the Vercel dashboard.
- **Offline Mode:** If connection to Vercel drops, JARVIS operates seamlessly offline with local voice and PC assistant tools.
