# Phase 4: AI Conversation Engine Privacy Policy & Data Handling 🛡️

**Project**: myoneAI — Tamil JARVIS  
**Subsystem**: AI Conversation Engine  
**Date**: 2026-10-07  

---

## 🔒 Privacy & Cloud Data Handling

### 1. What Text is Sent
Only user input messages and active short-term dialogue context (up to `AI_MAX_HISTORY_MESSAGES=12`) are transmitted to the configured cloud AI provider (e.g. Google Gemini, OpenAI, or Groq) to generate contextual conversational responses.

### 2. When Transmission Occurs
Transmission occurs **strictly on-demand** when the user sends a message or completes a voice utterance. The system does not stream background data or scan user files.

### 3. Local Storage & Ephemeral Context
- **No Permanent Conversation Storage**: Conversation history in Phase 4 is stored purely in volatile RAM during runtime.
- When the application shuts down or `conversation_manager.clear_history()` is called, all dialogue history is immediately purged.
- No chat logs or conversation transcripts are written to persistent disk files.

### 4. API Credential Protection
- API keys (`AI_API_KEY`) are loaded from `.env` via `pydantic-settings` and are never hardcoded.
- `SensitiveDataFilter` redacts API keys, Bearer tokens, and authorization headers from all structured logs.
- `.env` is ignored in Git and will never be committed to source control.
