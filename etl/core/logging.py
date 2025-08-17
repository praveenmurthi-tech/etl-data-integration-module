from __future__ import annotations
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import os

class NotInfoFilter(logging.Filter):
    """Filter that only allows WARNING and above (excludes INFO & DEBUG)."""
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= logging.WARNING  # keep WARNING, ERROR, CRITICAL

def setup_logging(level: str = "INFO", log_dir: str = "logs") -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # capture everything

    # Clear old handlers (avoid duplicates if called twice)
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, level.upper(), logging.INFO))
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Rotating file handler for INFO logs only
    fh_info = RotatingFileHandler(
        os.path.join(log_dir, "info.log"), maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    fh_info.setLevel(logging.INFO)
    fh_info.addFilter(lambda record: record.levelno == logging.INFO)  # only pure INFO
    fh_info.setFormatter(formatter)
    logger.addHandler(fh_info)

    # Rotating file handler for WARNING and above (excluding INFO/DEBUG)
    fh_err = RotatingFileHandler(
    os.path.join(log_dir, "error.log"),
    maxBytes=5_000_000,
    backupCount=5,
    encoding="utf-8"   
)

    fh_err.setLevel(logging.WARNING)  # WARNING, ERROR, CRITICAL
    fh_err.addFilter(NotInfoFilter())
    fh_err.setFormatter(formatter)
    logger.addHandler(fh_err)
