from __future__ import annotations
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import os

def setup_logging(level: str = "INFO", log_dir: str = "logs") -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(level.upper())

    # Console
    ch = logging.StreamHandler()
    ch.setLevel(level.upper())
    ch.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(ch)

    # Rotating File
    fh = RotatingFileHandler(os.path.join(log_dir, "app.log"), maxBytes=5_000_000, backupCount=5)
    fh.setLevel(level.upper())
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(fh)
