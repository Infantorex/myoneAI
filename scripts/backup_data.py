"""Production Data Backup Utility for myoneAI / Tamil JARVIS (Phase 15).

Creates a timestamped backup archive of local databases (memory.db, productivity.db)
and safe application configurations. Never backs up API keys, tokens, or raw audio.

Usage:
    python scripts/backup_data.py [--output-dir PATH]
"""

import argparse
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import shutil
import sys
from typing import Optional
import zipfile

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import __version__
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backup")


def create_backup(output_dir: Optional[Path] = None) -> Path:
    """Create a verified backup zip archive.

    Args:
        output_dir: Destination directory (defaults to PROJECT_ROOT/backups).

    Returns:
        Path to the created zip backup file.
    """
    settings = get_settings()
    backups_dir = output_dir or (PROJECT_ROOT / "backups")
    backups_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"myoneai_backup_v{__version__}_{timestamp}.zip"
    backup_path = backups_dir / backup_filename

    data_dir = settings.data_path

    logger.info("Starting backup process to '%s'...", backup_path)

    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        # 1. Back up Memory Database if exists
        mem_db = settings.memory_db_path
        if mem_db.exists():
            zipf.write(mem_db, arcname="memory.db")
            logger.info("  ✓ Added memory.db (%d bytes)", mem_db.stat().st_size)

        # 2. Back up Productivity Database if exists
        prod_db = data_dir / "productivity.db"
        if prod_db.exists():
            zipf.write(prod_db, arcname="productivity.db")
            logger.info("  ✓ Added productivity.db (%d bytes)", prod_db.stat().st_size)

        # 3. Add sanitized metadata manifest (Zero secrets)
        manifest = {
            "version": __version__,
            "timestamp": timestamp,
            "created_at_iso": datetime.now().isoformat(),
            "app_env": settings.app_env,
            "default_language": settings.default_language,
            "safe_config": settings.get_safe_dict(),
        }
        zipf.writestr("manifest.json", json.dumps(manifest, indent=2))
        logger.info("  ✓ Added manifest.json with sanitized metadata")

    logger.info("Backup successfully completed: %s (%d bytes)", backup_path.name, backup_path.stat().st_size)
    return backup_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup myoneAI databases and configurations")
    parser.add_argument("--output-dir", type=str, default=None, help="Optional custom output directory")
    args = parser.parse_args()

    out_p = Path(args.output_dir) if args.output_dir else None
    try:
        archive_path = create_backup(out_p)
        print(f"\n[SUCCESS] Backup created successfully:\n{archive_path}\n")
    except Exception as exc:
        logger.error("Backup failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
