"""Normalização de caminhos (Windows 8.3 → nome longo)."""

from __future__ import annotations

import sys
from pathlib import Path


def normalize_path(path: str | Path) -> Path:
    """Resolve caminho absoluto; no Windows expande nomes curtos (MATEMA~1)."""
    p = Path(path)
    if sys.platform == "win32":
        try:
            import ctypes

            buffer = ctypes.create_unicode_buffer(32768)
            get_long = ctypes.windll.kernel32.GetLongPathNameW
            if get_long(str(p), buffer, 32768):
                return Path(buffer.value).resolve()
        except OSError:
            pass
    return p.resolve()


def display_filename(path: str | Path) -> str:
    return normalize_path(path).name
