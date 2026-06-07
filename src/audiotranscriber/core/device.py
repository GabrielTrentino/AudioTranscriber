"""Detecção de dispositivo para Whisper (CPU / CUDA)."""

from __future__ import annotations


def cuda_available() -> bool:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def available_device_choices() -> list[tuple[str, str]]:
    """Rótulos da GUI e valores aceitos pelo faster-whisper."""
    choices: list[tuple[str, str]] = [("CPU", "cpu")]
    if cuda_available():
        choices.append(("GPU (CUDA)", "cuda"))
    return choices


def normalize_device(value: str) -> str:
    lowered = value.strip().lower()
    if lowered in ("cuda", "gpu"):
        return "cuda" if cuda_available() else "cpu"
    return "cpu"


def default_compute_type_for_device(device: str) -> str:
    return "float16" if normalize_device(device) == "cuda" else "int8"
