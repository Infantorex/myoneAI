# Phase 7: Controlled AI Memory Privacy Policy & Data Handling 🛡️

**Project**: myoneAI — Tamil JARVIS  
**Subsystem**: Controlled AI Memory System  
**Date**: 2026-10-07  

---

## 🔒 Privacy & Memory Management Policy

### 1. What Can Be Stored
- **User Preferences**: Spoken language preference (`Tamil` / `English`), response length/style (`short concise answers`).
- **Project Information**: Main project names, tools, technical stacks (`Vibrawave`).
- **Personal Context**: Non-sensitive contextual details explicitly provided by the user.
- **Explicit Instructions**: Reminders and notes explicitly commanded by the user ("Remember that...").

### 2. What is Strictly Forbidden & Automatically Rejected
The memory system enforces an automated privacy filter (`app/core/memory/privacy.py`). The following sensitive data will **never** be stored:
- ❌ Passwords, passcodes, and PINs
- ❌ API keys, Bearer tokens, and Secret keys
- ❌ OTPs and verification codes
- ❌ Bank account numbers and IBANs
- ❌ Credit and debit card numbers
- ❌ Private cryptographic keys and certificates
- ❌ Raw microphone audio recordings

Attempts to store forbidden credentials trigger an immediate rejection:
> *"I can't save sensitive credentials or private security information."*

### 3. Local Storage Location & Git Exclusion
- Memories are stored locally in an embedded SQLite database at `data/memory.db`.
- Database files (`data/*.db`, `data/*.sqlite`, `data/*.sqlite3`) are strictly ignored in `.gitignore` and are never committed or uploaded to Git repositories.

### 4. Data Transmission to AI Providers
- The entire memory database is **never** sent to cloud AI providers.
- Only the top most relevant memories matching the active user query (up to `MEMORY_MAX_RESULTS=5`, max 3,000 characters) are included in the prompt context to answer contextually.

### 5. Memory Deletion & Clear All Safeguards
Users have complete sovereignty over their data:
- **Delete Specific Memory**: Say *"Forget that my project is Vibrawave"* or *"Forget that I prefer Tamil"*.
- **Clear All Memories**: Say *"Clear all memories"*. Requires explicit user confirmation (*"Yes, clear memories"*) before records are permanently deleted.

### 6. Disabling the Memory Subsystem
Memory can be completely disabled at any time in `.env`:
```env
MEMORY_ENABLED=false
```
When disabled, JARVIS operates in a purely stateless conversational mode without querying or saving to the SQLite database.
