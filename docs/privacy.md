# Privacy Policy & Data Boundaries — myoneAI (v1.0.0)

**myoneAI** is built local-first to ensure complete confidentiality of your voice, files, and personal productivity data.

---

## 1. What Data is Collected & Where It Stays

| Data Type | Purpose | Storage Location | Retention |
| :--- | :--- | :--- | :--- |
| **Microphone Audio** | Speech recognition during active turn | **In-Memory RAM Only** | Destroyed immediately after speech-to-text. Never stored on disk. |
| **User Memory** | Remembers user-approved facts | **Local SQLite** (`data/memory.db`) | Stored locally until user deletes or clears. |
| **Tasks & Notes** | Productivity management | **Local SQLite** (`data/productivity.db`) | Stored locally. Never uploaded to public servers. |
| **Screenshots** | On-demand user screen inspection | **Local Folder** (`data/screenshots`) | Auto-purged after 7 days. |
| **Diagnostic Logs** | Local troubleshooting | **Local File** (`logs/jarvis.log`) | Rotated at 5 MB (max 15 MB). Sensitive keys automatically redacted. |

---

## 2. Audio Privacy & Microphone Access

- **No Continuous Cloud Streaming**: Background wake-word listening evaluates energy and acoustic patterns locally on your CPU (< 0.5% CPU load).
- **Ephemeral Audio Buffers**: Audio bytes are only sent to the STT provider during the few seconds after you say "JARVIS" or press the talk button.
- **Zero Audio Archives**: No `.wav` or `.mp3` audio files are ever written to your hard drive.

---

## 3. Sensitive Data Protection

The AI memory store automatically blocks passwords, API tokens, credit cards, bank accounts, and private keys using `validate_memory_content()`.

If you accidentally ask JARVIS to remember a password, it will refuse politely:
> *"பாதுகாப்பு காரணங்களால் கடவுச்சொற்கள் அல்லது ரகசிய குறியீடுகளை நினைவில் வைக்க முடியாது."*

---

## 4. User Controls

- **Reviewing Memories**: Ask *"What do you remember about me?"* or view in the Web Dashboard.
- **Deleting Memories**: Say *"Forget my project info"* or delete items from the dashboard.
- **Purging Data**: Run `scripts\backup_data.py` to create a local safe backup, or delete SQLite database files directly in `data/`.
