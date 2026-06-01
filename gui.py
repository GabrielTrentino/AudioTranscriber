"""Ponto de entrada da interface gráfica."""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from audiotranscriber.gui.app import TranscriberApp, main

__all__ = ["TranscriberApp", "main"]

if __name__ == "__main__":
    main()
