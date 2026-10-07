# Phase 9: System Monitoring & Telemetry Privacy Architecture

## Overview
**myoneAI — Tamil JARVIS** incorporates a strictly local, read-only, on-demand and bounded-periodic system monitoring architecture. Designed for privacy-first execution on resource-constrained personal hardware (Intel Core i3 10th Gen, 8 GB RAM), the system ensures hardware health visibility without compromising personal user data.

---

## 1. Data Collected vs Excluded

### Metrics Collected (Local Only)
- **CPU Metrics**: Instantaneous utilization percentage (`psutil.cpu_percent`), logical and physical core count, processor frequency.
- **Memory (RAM) Metrics**: Total physical memory, active used memory (MB/GB), free/available capacity (MB/GB), utilization percentage.
- **Disk Storage Metrics**: Primary mount drive capacity (total GB), free available space (GB), used capacity (GB), usage percentage.
- **Battery & Power Metrics**: Battery charge percentage, AC power connection state, charging indicator.
- **Network Telemetry**: Local connection status (boolean `is_connected`), hostname, outbound local IP address (without packet sniffing).
- **Process Summaries (On-Demand Only)**: Process ID (PID), process name, memory footprint (MB), and CPU utilization for the top 5 resource consumers.

### Strict Privacy Exclusions (Zero Collection)
- ❌ **No Screen Captures / Continuous OCR**: Screen is never monitored in the background.
- ❌ **No Webcam / Optical Sensors**: Camera is never accessed for monitoring.
- ❌ **No Keylogging or Keystroke Interception**: Keystroke dynamics and input events are never recorded.
- ❌ **No Arbitrary Filesystem Indexing**: System folders, personal user files, and browser histories are never continuously indexed.
- ❌ **No Packet Sniffing / Deep Packet Inspection**: Network traffic content, payloads, and visited URLs are never inspected.
- ❌ **No Full Process Tree Tracing**: Background daemons and child threads are not continuously traced.
- ❌ **No Credential Access**: Passwords, tokens, browser cookies, and keychain secrets are strictly excluded.

---

## 2. Monitoring Frequency & Lifecycle

1. **On-Demand (User Voice/Text Request)**:
   - Evaluated only at the exact instant the user requests information (e.g., *"Jarvis, how is my laptop?"*, *"Check RAM"*, *"Why is my laptop slow?"*).
   - Once metrics are returned, sampling immediately ceases.

2. **Periodic Background Health Checker**:
   - Executes at a configurable, low-frequency interval (default: `MONITORING_INTERVAL_SECONDS=60`).
   - Only reads lightweight counters (CPU, RAM, Disk, Battery).
   - Process tables and latency tests are **never** scanned in the background loop to maintain near-zero CPU/RAM impact.

---

## 3. Storage & AI Transmission Policy

- **Ephemeral In-Memory Storage**: Telemetry snapshots exist solely in-memory during request processing or within a small in-memory ring buffer (maximum 50 recent alert entries).
- **No Permanent Metrics Database**: Telemetry is never written to disk databases or sqlite storage.
- **No Continuous Telemetry Uploads**: Metrics are never streamed or uploaded to any third-party or cloud telemetry service.
- **AI Transmission Policy**: Only summarized strings (e.g. `CPU: 32% | RAM: 68%`) are passed to the AI conversation engine during explicit user queries to enable natural conversational responses. When idle, no telemetry is transmitted to AI providers.

---

## 4. Disabling System Monitoring

System monitoring can be completely disabled at any time via configuration.

In `.env`:
```env
MONITORING_ENABLED=false
```

When set to `false`, the background health checker will not start, no background threads/tasks are created, and on-demand tools can only be invoked manually if requested.
