"""Ponto de entrada da API HTTP (raiz do repositório)."""

import _path_setup  # noqa: F401

from audiotranscriber.api.app import app

__all__ = ["app"]
