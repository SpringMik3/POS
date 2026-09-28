import logging

from modules.app_paths import ensure_app_dirs, resolve_app_path


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging():
    ensure_app_dirs()
    log_path = resolve_app_path("logs", "app.log")
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if not any(isinstance(handler, logging.FileHandler) and getattr(handler, "baseFilename", None) == str(log_path) for handler in root_logger.handlers):
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root_logger.addHandler(file_handler)

    return log_path


def get_logger(name):
    setup_logging()
    return logging.getLogger(name)
