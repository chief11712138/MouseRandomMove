from __future__ import annotations

import sys
from pathlib import Path


def package_root() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS"))
        return base / "mouse_random_move"
    return Path(__file__).resolve().parent


def frontend_root() -> Path:
    return package_root() / "frontend"

