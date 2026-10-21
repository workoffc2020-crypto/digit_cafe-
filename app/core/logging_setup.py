"""Local error logging. Logs never leave the computer."""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def log_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, "CyberCafeStudio", "logs")
    os.makedirs(path, exist_ok=True)
    return path


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("ccs")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fh = RotatingFileHandler(os.path.join(log_dir(), "app.log"), maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)

    def hook(exc_type, exc, tb):
        logger.error("Unhandled exception", exc_info=(exc_type, exc, tb))
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = hook
    return logger
