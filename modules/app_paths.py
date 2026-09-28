import shutil
import sys
from pathlib import Path


DATABASE_NAME = "pos_database.db"


def get_app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def get_bundle_dir():
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return Path(bundle_dir).resolve()
    return get_app_dir()


def resolve_app_path(*parts):
    return get_app_dir().joinpath(*parts)


def resolve_bundle_path(*parts):
    return get_bundle_dir().joinpath(*parts)


def ensure_app_dirs():
    for dirname in ("logs", "reports", "exports", "receipts", "backups"):
        resolve_app_path(dirname).mkdir(parents=True, exist_ok=True)


def configure_app_logging():
    from modules.app_logger import setup_logging
    return setup_logging()


def get_database_path(db_name=DATABASE_NAME):
    target_path = resolve_app_path(db_name)

    if not target_path.exists() and getattr(sys, "frozen", False):
        bundled_db = resolve_bundle_path(db_name)
        if bundled_db.exists():
            shutil.copy2(bundled_db, target_path)

    return target_path
