"""Logger centralise (loguru)."""
from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from src.config.settings import ROOT_DIR

LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - {message}",
)
logger.add(
    LOG_DIR / "pipeline_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    rotation="10 MB",
    retention="14 days",
    encoding="utf-8",
)

__all__ = ["logger"]
