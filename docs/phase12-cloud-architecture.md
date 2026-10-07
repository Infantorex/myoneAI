# Phase 12 — Secure Laptop ↔ Vercel Communication Architecture

## Overview
The **myoneAI** Phase 12 architecture establishes a **secure, outbound-only communication bridge** connecting the local Windows assistant (`myoneAI`) with the Vercel-hosted Cloud Control Plane and Dashboard.

---

## 1. Core Architectural Topology

```text
                                INTERNET
                                   │
                                   ▼
                          ┌─────────────────┐
                          │ Vercel Frontend │
                          │   Dashboard     │
                          └────────┬────────┘
                                   │ HTTPS
                                   ▼
                          ┌─────────────────┐
                          │ Cloud API /     │
                          │ Control Plane   │
                          └────────┬────────┘
                                   │
                             Secure Outbound
                             HTTPS Connection
                                   │
                                   ▼
                          ┌─────────────────┐
                          │ Local myoneAI   │
                          │ Windows Agent   │
                          └────────┬────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │ Permission      │
                          │ Manager         │
                          └────────┬────────┘
                                   │
                                   ▼
                          Local Tools / Core
```

---

## 2. Security Boundaries & Directives

1. **No Inbound Windows Ports:**
   - The local Windows laptop NEVER binds to `0.0.0.0` or exposes open ports to the public internet.
   - Zero router port forwarding or public IP exposure.
   - All communication is initiated via **secure outbound HTTPS requests** from the laptop to the Cloud Control Plane.

2. **The Assistant Stays Local:**
   - Voice detection, microphone capture, STT, AI persona, TTS, local PC tools, SQLite memory, and productivity systems remain 100% on the local laptop.
   - Vercel functions strictly as a remote monitoring dashboard and control plane.

3. **HMAC-SHA256 Request Signing:**
   - Every message exchanged between Laptop and Cloud is signed with HMAC-SHA256 over `(id, type, timestamp, device_id, status, canonical_payload)`.
   - Incoming messages are validated using constant-time comparison (`hmac.compare_digest`).

4. **Sliding-Window Replay Protection:**
   - Messages older than 300 seconds (or in the future > 30 seconds) are rejected.
   - Request IDs are tracked in a sliding-window cache to prevent replay attacks.

5. **Strict Permission Tier Enforcement:**
   - Cloud commands route through `PermissionManager` (Phase 8).
   - `BLOCKED` tools are permanently rejected.
   - `CONFIRM` tools require local user approval (`status="confirmation_required"`).
   - Zero arbitrary shell command execution (`eval`, `exec`, `shell=True`).

---

## 3. Resilience & Offline Mode

- **Non-blocking Offline Resilience:** When the laptop is disconnected from the internet, JARVIS continues operating normally offline without crashing or blocking.
- **Exponential Backoff:** Outbound reconnect attempts follow a progressive backoff (2s → 4s → 8s → 16s → 32s → max 60s).
- **Bounded Offline Queue:** Safe synchronization events are stored in an in-memory queue (max 100 items). Old items are discarded on overflow; sensitive credentials and raw audio are strictly barred from the queue.
