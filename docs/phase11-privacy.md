# Phase 11 — Local Web Dashboard Privacy Architecture

## Overview

The `myoneAI` Web Dashboard is designed with a **privacy-first, local-only architecture**. The dashboard acts strictly as a lightweight user interface for the local assistant running on the user's Windows laptop.

> **CRITICAL ARCHITECTURAL POLICY:**  
> The local dashboard is not intended to be publicly exposed to the internet or external networks.

---

## 1. Localhost Isolation

- **Binding Address:** The API binds exclusively to loopback interface `127.0.0.1`.
- **Public Exposure:** Binding to `0.0.0.0` or opening ports to the public internet is strictly forbidden.
- **Port:** Configured by default to port `8000` (configurable via `WEB_PORT` in `.env`).

---

## 2. Authentication & Access Control

- **Token Protection:** If `WEB_AUTH_ENABLED=true`, all API calls require a Bearer token matching `WEB_AUTH_TOKEN`.
- **Constant-Time Verification:** Authentication checks use `secrets.compare_digest` to prevent timing attacks.
- **Client Storage:** Authentication tokens are stored solely in the client browser's `localStorage` session and never transmitted to third parties.

---

## 3. Data Privacy & Leakage Prevention

| Component | Privacy Safeguard |
| :--- | :--- |
| **API Keys & Secrets** | Never exposed to the browser. AI, STT, TTS, and Wake-word API keys remain strictly server-side in `.env`. |
| **Dashboard Home** | Displays only aggregated memory count; private memory records are never rendered on the homepage. |
| **Memory Management** | Direct SQLite access from frontend is forbidden. Memory reads/writes pass through `MemoryManager` with sensitive credential filters. Clear all memories requires explicit confirmation. |
| **Activity Feed** | Filtered through `SensitiveDataFilter` to mask API keys, tokens, and sensitive strings. Raw audio, passwords, and file contents are never logged to the activity feed. |
| **Error Handling** | Structured JSON error messages with sanitized explanations. Python tracebacks and internal file paths are masked from API responses. |
| **XSS Protection** | Client renders dynamic data using DOM `textContent` properties, preventing script injection. |

---

## 4. Hardware Telemetry Privacy

- Hardware monitoring is collected locally via `psutil`.
- Diagnostic data reflects CPU, RAM, Disk, and Battery metrics without transmitting telemetry to any external cloud provider.
- Polling frequency is throttled (default 10s) to minimize background resource overhead.
