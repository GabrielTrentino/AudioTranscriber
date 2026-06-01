"""Backend de diarização: local (padrão), pyannote ou whisperx via env."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def diarization_backend_name() -> str:
    return os.getenv("DIARIZATION_BACKEND", "local").strip().lower()


def is_diarization_available() -> bool:
    name = diarization_backend_name()
    if name == "whisperx":
        from audiotranscriber.services.diarization import is_diarization_available

        return is_diarization_available()
    if name == "pyannote":
        from audiotranscriber.services.diarization_pyannote import is_pyannote_available

        return is_pyannote_available()
    from audiotranscriber.services.diarization_local import is_local_diarization_available

    return is_local_diarization_available()


def diarization_install_hint() -> str:
    name = diarization_backend_name()
    if name == "whisperx":
        from audiotranscriber.services.diarization import diarization_install_hint

        return diarization_install_hint()
    if name == "pyannote":
        from audiotranscriber.services.diarization_pyannote import install_hint

        return install_hint()
    from audiotranscriber.services.diarization_local import install_hint

    return install_hint()


def assign_speaker_labels(
    audio_path: Path,
    segments: list[Any],
    *,
    device: str = "cpu",
    language: str | None = None,
) -> list[dict[str, Any]]:
    name = diarization_backend_name()
    if name == "whisperx":
        from audiotranscriber.services.diarization import assign_speakers

        return assign_speakers(
            audio_path, segments, device=device, language=language
        )
    if name == "pyannote":
        from audiotranscriber.services.diarization_pyannote import assign_speakers

        return assign_speakers(audio_path, segments, device=device, language=language)

    from audiotranscriber.services.diarization_local import assign_speakers

    return assign_speakers(audio_path, segments, device=device, language=language)
