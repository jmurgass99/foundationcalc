"""Util compartido para jobs."""
from __future__ import annotations
import os
import sys
from pathlib import Path


def data_dir() -> Path:
    """Carpeta de datos del usuario para FoundationDesignJm jobs."""
    env = os.environ.get("FOUNDATIONDESIGNJM_DATA_DIR")
    if env:
        return Path(env)
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", str(Path.home()))) / "foundationdesignjm"
    return Path.home() / ".foundationdesignjm"
