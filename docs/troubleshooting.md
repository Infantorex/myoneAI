# Troubleshooting Guide — myoneAI (v1.0.0)

Solutions for common hardware, network, and audio issues.

---

## 1. Pre-Flight Diagnostic

Always start by running the health check:

```powershell
python -m app.core.health
```

If any check returns `FAIL`, refer to the sections below.

---

## 2. Audio & Microphone Issues

### Problem: Wake word is not triggering
- **Fix**: Check microphone default input device in Windows Sound Settings (`mmsys.cpl`).
- **Fix**: Ensure your microphone volume is at 80%+ and not muted physically.
- **Fix**: In `.env`, lower `WAKE_WORD_SENSITIVITY=0.4` or lower `VAD_ENERGY_THRESHOLD=350.0`.

### Problem: TTS speech is not playing
- **Fix**: Verify speaker output is working in Windows.
- **Fix**: Check Edge-TTS connectivity. If offline, the assistant handles TTS failures gracefully without crash.

---

## 3. AI & API Key Issues

### Problem: "JARVIS could not connect to AI service"
- **Fix**: Check your internet connection.
- **Fix**: Check that `AI_API_KEY` in `.env` is valid and does not start with `your_`.
- **Fix**: If using Gemini, test with `AI_MODEL=gemini-1.5-flash`.

---

## 4. Single Instance / Lock Issues

### Problem: "Another instance of myoneAI is already running"
- **Fix**: Run `scripts\stop_myoneai.bat` to kill orphan background processes.
- **Fix**: If the previous run crashed abnormally, delete `data\myoneai.lock` manually.

---

## 5. Web Dashboard Port Conflict

### Problem: Port 8000 is already in use
- **Fix**: Change `WEB_PORT=8080` in `.env` and restart `python -m web.api.server`.

---

## 6. Corrupt Database Recovery

### Problem: Database integrity check fails
- **Fix**: Restore from the latest backup:
  ```powershell
  python scripts/restore_data.py --backup-file backups/myoneai_backup_v1.0.0_XXXXX.zip
  ```
