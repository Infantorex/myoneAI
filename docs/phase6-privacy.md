# Phase 6: Wake Word System Privacy Policy & Audio Lifecycle 🛡️

**Project**: myoneAI — Tamil JARVIS  
**Subsystem**: Lightweight Wake Word Detection  
**Date**: 2026-10-07  

---

## 🔒 Privacy & Audio Lifecycle

### 1. Microphone State & Wake Processing
- **Local Audio Processing**: Wake-word listening operates on local audio chunks and does **NOT** stream continuous background audio to any cloud server or third-party API.
- **Low-Power Energy Filtering**: Background silence is discarded in memory (< 0.1% CPU).

### 2. Audio Storage Policy
- **Zero Permanent Audio Storage**: Ambient audio chunks examined during wake listening are ephemeral and reside strictly in volatile RAM.
- No audio files, snippets, or recordings are written to disk during wake-word detection or conversation turns.

### 3. When Audio Leaves the Laptop
- Background ambient audio while waiting for "JARVIS" **never leaves the device**.
- External cloud transmission occurs **only after** the wake word is confirmed and the assistant explicitly transitions to the active `LISTENING` state for the user's specific query.
- Only the recorded query audio WAV is sent to the configured STT provider (e.g. Google / Groq).

### 4. Microphone Handover & Resource Release
- When the wake word is detected, the wake listening stream is paused and released.
- The conversation pipeline acquires the microphone for the duration of the utterance, records the query, and instantly releases the microphone hardware.
- Upon `Ctrl+C` interrupt or error, all audio hardware streams and buffers are immediately closed.

### 5. Disabling Wake-Word Detection
Wake-word detection is completely optional and can be disabled at any time:
- In `.env`:
  ```env
  WAKE_WORD_ENABLED=false
  ```
- Or use manual voice mode fallback:
  ```powershell
  python -m app.voice.conversation
  ```
