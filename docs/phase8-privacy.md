# Phase 8: Secure PC Assistant Tools Privacy Policy & Data Boundaries 🛡️

**Project**: myoneAI — Tamil JARVIS  
**Subsystem**: Secure PC Assistant Tools & Permissions  
**Date**: 2026-10-07  

---

## 🔒 Privacy & Data Boundary Policy

### 1. What PC Information JARVIS Can Access
JARVIS provides safe, read-only system telemetry designed to monitor laptop health without compromising personal privacy:
- **CPU & RAM Load**: Overall system utilization percentages and total/available memory.
- **Battery Status**: Charge percentage, AC power connection state, and estimated runtime.
- **Disk Free Space**: Available and total storage capacity on the active project drive.
- **OS & Host Information**: Operating system name, version architecture, and machine hostname.

### 2. Accessible Directories
Filesystem operations are strictly confined to an explicit allowlist:
- **Default Allowed Folders**:
  - `E:\myoneAI-phase1-foundation` (Project workspace)
  - `~/Documents`, `~/Downloads`, `~/Desktop`, `~/Pictures`, `~/Music`, `~/Videos`
  - `data/` (Local data directory)
- **Blocked System Directories**:
  - `C:\Windows`, `C:\Windows\System32`, `C:\Windows\SysWOW64`
  - `C:\Program Files`, `C:\Program Files (x86)`
  - `~/.ssh`, `~/.aws`, `AppData/Local/Microsoft/Credentials`

### 3. Application Launch Allowlist
JARVIS cannot execute arbitrary binaries or download untrusted scripts. Only pre-approved applications are accessible:
- **Web Browsers**: Google Chrome (`chrome`), Microsoft Edge (`msedge`), Brave, Firefox.
- **Productivity & Editors**: Visual Studio Code (`code`), Notepad (`notepad`), Calculator (`calc`), Wordpad (`write`), Paint (`mspaint`).
- **System Utilities**: File Explorer (`explorer`), Task Manager (`taskmgr`).

### 4. Screenshot Behavior & Local Retention
- **On-Demand Only**: Screenshots are only taken when the user explicitly commands (e.g., *"Jarvis, take a screenshot"* or *"Screenshot எடு"*).
- **Zero Background Captures**: Screen capture is never executed continuously or in the background.
- **Local Storage**: Saved strictly locally in `data/screenshots/screenshot_YYYYMMDD_HHMMSS.bmp`.
- **Zero Cloud Uploads**: Screenshots are never automatically uploaded to cloud servers or AI providers in Phase 8.
- **7-Day Retention Cleanup**: Screenshots older than `SCREENSHOT_RETENTION_DAYS=7` are automatically purged during capture cycles.

### 5. What Information Is Sent to AI
- Only tool execution outcome messages (e.g., *"RAM usage is 72%"* or *"Application Chrome opened"*) are fed into the conversation context to formulate natural spoken replies.
- Raw file contents, credential strings, database tables, and image buffers are **never** transmitted to the AI provider.

### 6. What Information Is Never Stored
- ❌ No user passwords, authentication tokens, or private SSH keys
- ❌ No clipboard contents or keystroke logs
- ❌ No continuous audio recording beyond spoken command interaction
- ❌ No automatic cloud backups of user files or folders

### 7. Disabling PC Assistant Tools
Tools can be completely disabled at any time in `.env`:
```env
TOOLS_ENABLED=false
```
When disabled, JARVIS operates in a purely conversational mode and will reject all PC control requests.
