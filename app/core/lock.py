"""Cross-process single-instance lock for myoneAI / Tamil JARVIS (Phase 15).

Prevents duplicate instances of wake-word listeners, audio streams, schedulers,
and servers from running concurrently on the Windows machine.
"""

import logging
import os
from pathlib import Path
import sys
from typing import Optional

from app.core.config import PROJECT_ROOT

logger = logging.getLogger("myoneAI.core.lock")


class SingleInstanceLock:
    """Acquires an exclusive OS-level file lock to guarantee single-instance execution."""

    def __init__(self, lock_file_path: Optional[Path] = None) -> None:
        self.lock_file_path = lock_file_path or (PROJECT_ROOT / "data" / "myoneai.lock")
        self._lock_file = None
        self._is_locked = False

    def acquire(self) -> bool:
        """Attempt to acquire the single-instance lock.

        Returns:
            True if lock was acquired successfully; False if another instance is already running.
        """
        try:
            self.lock_file_path.parent.mkdir(parents=True, exist_ok=True)
            self._lock_file = open(self.lock_file_path, "a+")

            if sys.platform == "win32":
                import msvcrt
                try:
                    # Seek to start and try non-blocking lock of 1 byte
                    self._lock_file.seek(0)
                    msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    # Write current PID
                    self._lock_file.seek(0)
                    self._lock_file.truncate()
                    self._lock_file.write(f"{os.getpid()}\n")
                    self._lock_file.flush()
                    self._is_locked = True
                    logger.debug("Acquired single-instance lock on %s (PID %d)", self.lock_file_path, os.getpid())
                    return True
                except (IOError, OSError):
                    logger.warning("Another instance of myoneAI is already running. Lock on '%s' denied.", self.lock_file_path)
                    return False
            else:
                import fcntl
                try:
                    fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self._lock_file.seek(0)
                    self._lock_file.truncate()
                    self._lock_file.write(f"{os.getpid()}\n")
                    self._lock_file.flush()
                    self._is_locked = True
                    return True
                except (IOError, OSError):
                    logger.warning("Another instance of myoneAI is already running.")
                    return False
        except Exception as exc:
            logger.error("Failed to check single-instance lock: %s", exc)
            return True  # Fallback to permissive if locking mechanism has filesystem issue

    def release(self) -> None:
        """Release the lock upon shutdown."""
        if not self._is_locked or not self._lock_file:
            return

        try:
            if sys.platform == "win32":
                import msvcrt
                self._lock_file.seek(0)
                msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
            self._lock_file.close()
            self._is_locked = False
            logger.debug("Released single-instance lock.")
        except Exception as exc:
            logger.debug("Error releasing lock: %s", exc)


# Global instance
single_instance_lock = SingleInstanceLock()
