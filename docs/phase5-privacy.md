# Phase 5: Voice Conversation Loop Privacy Policy & Data Handling 🛡️

**Project**: myoneAI — Tamil JARVIS  
**Subsystem**: Natural Voice Conversation Loop  
**Date**: 2026-10-07  

---

## 🔒 Privacy & Audio Data Lifecycle

### 1. When Microphone Activates
- **Microphone is OFF by default**: Starting the core application (`python -m app.core.main`) does **not** activate the microphone.
- Microphone hardware is only opened when the user explicitly triggers voice mode via `python -m app.voice.conversation` (or interactive mode `--interactive`).

### 2. When Audio is Captured
- Audio is only captured in short bursts while in the `LISTENING` state.
- Voice Activity Detection (VAD) monitors RMS energy levels to detect user speech, capturing audio only while the user is actively speaking, followed by silence cutoff.

### 3. Where Audio Data is Stored
- **100% In-Memory (RAM)**: Captured audio frames are buffered directly in RAM using NumPy and in-memory `io.BytesIO` WAV containers.
- **Zero Disk Storage**: No temporary audio files (`.wav`, `.mp3`) or raw recording snippets are ever written to the hard drive or SSD.

### 4. When Audio Data is Deleted
- Audio memory buffers are immediately dereferenced and garbage collected as soon as speech recognition completes.
- In the event of an error, timeout, or interruption, audio buffers and hardware streams are instantly freed in `finally` cleanup blocks.

### 5. External Cloud Transmissions
- **STT (Speech-to-Text)**: Audio WAV bytes are transmitted over HTTPS to the configured STT provider (e.g. Google Speech API or Groq Whisper API) solely to obtain the text transcript.
- **AI Engine**: Text transcript and short-term dialogue context (up to `AI_MAX_HISTORY_MESSAGES=12`) are transmitted over TLS to the configured AI provider (Google Gemini or OpenAI-compatible endpoint).
- **TTS (Text-to-Speech)**: Response text is transmitted to Microsoft Edge Neural TTS over WSS/HTTPS to generate audio stream packets.

### 6. No Raw Audio or Transcript Logging
- Raw microphone audio is never logged or dumped.
- Structured application logs record only state transitions and operational metrics; private credentials and sensitive tokens are masked by `SensitiveDataFilter`.
- Dialogue context is strictly in-memory and volatile; no conversation transcripts are written to persistent storage in Phase 5.

### 7. How to Stop the Assistant
Users maintain complete control and can stop the voice loop at any time:
- **Voice / Text Command**: Say or type `exit`, `quit`, or `stop`.
- **Keyboard Interrupt**: Press `Ctrl+C` in the terminal for clean, instantaneous shutdown and audio resource release.
