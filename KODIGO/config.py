"""Application configuration."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "KODIGO"
APP_TAGLINE = "QR Code Studio"
APP_VERSION = "1.0.0"


def resource_path(relative: str) -> str:
    """Resource path."""
    base = getattr(sys, "_MEIPASS", None) or Path(__file__).resolve().parent.parent
    return str(Path(base) / relative)


def user_data_dir() -> Path:
    """User data directory."""
    if sys.platform.startswith("win"):
        root = Path(os.environ.get("APPDATA") or Path.home())
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    path = root / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


DB_PATH = user_data_dir() / "history.db"
