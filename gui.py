"""Ponto de entrada da interface gráfica (raiz do repositório)."""

import _path_setup  # noqa: F401

from audiotranscriber.gui.app import TranscriberApp, main

__all__ = ["TranscriberApp", "main"]

if __name__ == "__main__":
    main()
