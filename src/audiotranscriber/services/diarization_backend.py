"""Escolhe backend de diarização (pyannote experimental ou whisperx legado)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def diarization_backend_name() -> str:
    return os.getenv("DIARIZATION_BACKEND", "pyannote").strip().lower()


def is_diarization_available() -> bool:
    if diarization_backend_name() == "whisperx":
        from audiotranscriber.services.diarization import is_diarization_available

        return is_diarization_available()
    from audiotranscriber.services.diarization_pyannote import is_pyannote_available

    return is_pyannote_available()


def diarization_install_hint() -> str:
    if diarization_backend_name() == "whisperx":
        from audiotranscriber.services.diarization import diarization_install_hint

        return diarization_install_hint()
    from audiotranscriber.services.diarization_pyannote import install_hint

    return install_hint()


def assign_speaker_labels(
    audio_path: Path,
    segments: list[Any],
    *,
    device: str = "cpu",
    language: str | None = None,
) -> list[dict[str, Any]]:
    if diarization_backend_name() == "whisperx":
        from audiotranscriber.services.diarization import assign_speakers

        return assign_speakers(
            audio_path, segments, device=device, language=language
        )

    from audiotranscriber.services.diarization_pyannote import assign_speakers

    return assign_speakers(audio_path, segments, device=device, language=language)
