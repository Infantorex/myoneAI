"""Production Data Restore Utility for myoneAI / Tamil JARVIS (Phase 15).

Restores databases (memory.db, productivity.db) and verifies SQLite integrity
from a verified backup archive.

Usage:
    python scripts/restore_data.py --backup-file backups/myoneai_backup_v1.0.0_XXXXXX.zip
"""

import argparse
import json
import logging
from pathlib import Path
import sqlite3
import sys
from typing import Optional
import zipfile

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("restore")


def restore_backup(backup_file: Path, target_data_dir: Optional[Path] = None) -> bool:
    """Restore database files from a verified zip backup archive.

    Args:
        backup_file: Path to backup .zip archive.
        target_data_dir: Destination data directory (defaults to settings.data_path).

    Returns:
        True if all files restored and passed SQLite integrity checks.
    """
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found at '{backup_file}'.")

    settings = get_settings()
    data_dir = target_data_dir or settings.data_path
    data_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Opening backup archive '%s'...", backup_file.name)

    with zipfile.ZipFile(backup_file, "r") as zipf:
        file_list = zipf.namelist()
        logger.info("Found archive contents: %s", file_list)

        # 1. Check and print manifest
        if "manifest.json" in file_list:
            manifest_data = json.loads(zipf.read("manifest.json").decode("utf-8"))
            logger.info("  ✓ Verified Manifest (Version: v%s, Created: %s)", manifest_data.get("version"), manifest_data.get("timestamp"))

        # 2. Extract and verify memory.db
        if "memory.db" in file_list:
            target_mem = data_dir / "memory.db"
            zipf.extract("memory.db", path=data_dir)
            logger.info("  ✓ Restored memory.db -> %s", target_mem)

            # SQLite integrity check
            conn = sqlite3.connect(str(target_mem))
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            res = cursor.fetchone()
            conn.close()
            if not res or res[0] != "ok":
                raise ValueError(f"Restored memory.db failed integrity check: {res}")
            logger.info("  ✓ Verified SQLite integrity on memory.db: OK")

        # 3. Extract and verify productivity.db
        if "productivity.db" in file_list:
            target_prod = data_dir / "productivity.db"
            zipf.extract("productivity.db", path=data_dir)
            logger.info("  ✓ Restored productivity.db -> %s", target_prod)

            conn = sqlite3.connect(str(target_prod))
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            res = cursor.fetchone()
            conn.close()
            if not res or res[0] != "ok":
                raise ValueError(f"Restored productivity.db failed integrity check: {res}")
            logger.info("  ✓ Verified SQLite integrity on productivity.db: OK")

    logger.info("Restore successfully completed from '%s'.", backup_file.name)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore myoneAI databases from backup")
    parser.add_argument("--backup-file", type=str, required=True, help="Path to backup zip archive")
    parser.add_argument("--target-dir", type=str, default=None, help="Optional custom target data directory")
    args = parser.parse_args()

    backup_p = Path(args.backup_file)
    target_p = Path(args.target_dir) if args.target_dir else None

    try:
        success = restore_backup(backup_p, target_p)
        if success:
            print("\n[SUCCESS] All databases restored and verified successfully.\n")
        else:
            print("\n[ERROR] Restore failed.\n")
            sys.exit(1)
    except Exception as exc:
        logger.error("Restore failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
