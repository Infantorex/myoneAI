# Production Rollback Guide — myoneAI (v1.0.0)

If an update fails or unexpected behavior occurs after updating code, follow this rollback procedure.

---

## 1. Automated Rollback

If you created a backup prior to updating, restore the state:

```powershell
# 1. Stop any running assistant instances
scripts\stop_myoneai.bat

# 2. Revert Git code to known stable tag
git checkout v1.0.0

# 3. Restore database snapshot
python scripts/restore_data.py --backup-file backups/myoneai_backup_v1.0.0_XXXXX.zip

# 4. Re-install dependencies
pip install -r requirements.txt

# 5. Run health check
python -m app.core.health

# 6. Restart JARVIS
scripts\start_myoneai.bat
```

---

## 2. Emergency Clean Reset

To reset databases without losing settings:

```powershell
# Stop assistant
scripts\stop_myoneai.bat

# Delete lock file if stuck
del /f /q data\myoneai.lock

# Start assistant (databases will auto-initialize cleanly)
scripts\start_myoneai.bat
```
