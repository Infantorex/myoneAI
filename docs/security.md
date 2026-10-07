# Security Architecture & Policies — myoneAI (v1.0.0)

**myoneAI** implements rigorous defensive security boundaries engineered to prevent arbitrary execution, credential exfiltration, and unauthorized system access.

---

## 1. Zero Arbitrary Shell Execution Guarantee

The AI language model has **no direct access to shell or terminal interpreters**.
- Code analysis confirms **0 occurrences** of:
  - `os.system()`
  - `subprocess.Popen(..., shell=True)`
  - `eval()`
  - `exec()`
- All user requests are routed through a structured parser (`parse_tool_intent`) that maps text exclusively to statically registered Python methods in `ToolRegistry`.

---

## 2. Three-Tier Permission Model

Every executable capability is evaluated by `PermissionManager` against 3 distinct tiers:

1. **`SAFE` (Automated)**:
   - Read-only diagnostics (`get_system_status`, `get_battery_status`, `get_cpu_usage`).
   - Launching allowlisted applications (`chrome`, `notepad`, `calc`, `vscode`).
   - Standard browser search and volume controls.
2. **`CONFIRMATION_REQUIRED` (Human-in-the-Loop)**:
   - File deletion (`delete_file`).
   - Application termination (`close_application`).
   - Purging all tasks, memories, or notes.
   - Requires explicit verbal ("Yes" / "உறுதிப்படுத்துகிறேன்") or UI token confirmation. Tokens expire after 30 seconds.
3. **`BLOCKED` (Permanently Denied)**:
   - Shell commands (`powershell`, `cmd.exe`, `bash`).
   - Registry manipulation (`reg add`, `reg delete`).
   - User account modifications (`net user`).
   - Script download utilities (`curl`, `wget`, `certutil`, `bitsadmin`).

---

## 3. Filesystem Sandboxing

- File tools resolve canonical paths (`Path.resolve()`) and reject directory traversal attempts (`../`, `..\..`).
- System-critical Windows directories (`C:\Windows`, `System32`, `Program Files`) and credential directories (`.ssh`, `.aws`, `AppData\Local\Microsoft\Credentials`) are completely inaccessible.

---

## 4. Network Security & Localhost Isolation

- Local FastAPI REST API binds exclusively to `127.0.0.1`.
- Public wildcard (`0.0.0.0`) bindings are strictly prohibited.
- CORS headers restrict browser origins exclusively to localhost ports.

---

## 5. Cloud Bridge Security (Vercel)

- **HMAC-SHA256 Signing**: Every message between Laptop and Vercel is cryptographically signed.
- **Replay Protection**: Timestamp freshness (300s window) + cached nonces prevent replay attacks.
- **Air-Gap Safety**: Remote cloud commands must still pass local `PermissionManager` checks.
