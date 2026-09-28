import shutil
from datetime import datetime
from pathlib import Path

from modules.app_paths import resolve_app_path
from modules.app_logger import get_logger


logger = get_logger(__name__)


class BackupService:
    def __init__(self, database_path, backup_dir=None):
        self.database_path = Path(database_path)
        self.backup_dir = Path(backup_dir) if backup_dir else resolve_app_path("backups")

    def backup_database(self, reason="manual"):
        if not self.database_path.exists():
            logger.error("Database backup failed because source file does not exist: %s reason=%s", self.database_path, reason)
            raise FileNotFoundError(f"Database file not found: {self.database_path}")

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"pos_database_{timestamp}.db"

        try:
            shutil.copy2(self.database_path, backup_path)
            logger.info("Database backup created: %s reason=%s", backup_path, reason)
            return backup_path
        except Exception:
            logger.exception("Database backup failed: source=%s target=%s reason=%s", self.database_path, backup_path, reason)
            raise
