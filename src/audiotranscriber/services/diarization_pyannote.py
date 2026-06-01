"""
Diarização com pyannote (community-1) — módulo experimental, separado do core.

Requisitos:
  pip install "audiotranscriber[diarization]"
  Aceitar termos em https://huggingface.co/pyannote/speaker-diarization-community-1
  Variável HF_TOKEN (ou HUGGINGFACE_TOKEN) com token de leitura.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

_PIPELINE_ID = "pyannote/speaker-diarization-community-1"


class PyannoteNotAvailableError(ImportError):
    """pyannote.audio não instalado ou token HF ausente."""


def is_pyannote_available() -> bool:
    try:
        import pyannote.audio  # noqa: F401

        return True
    except ImportError:
        return False


def install_hint() -> str:
    return (
        "Instale: pip install \"audiotranscriber[diarization]\"\n"
        "Aceite os termos do modelo no Hugging Face e defina HF_TOKEN."
    )


def _hf_token() -> str | None:
    for key in ("HF_TOKEN", "HUGGINGFACE_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return None


@lru_cache(maxsize=1)
def _load_pipeline(device: str):
    import torch
    from pyannote.audio import Pipeline

    token = _hf_token()
    if not token:
        raise PyannoteNotAvailableError(
            "Token Hugging Face ausente. Defina HF_TOKEN no ambiente.\n" + install_hint()
        )

    pipeline = Pipeline.from_pretrained(_PIPELINE_ID, token=token)
    torch_device = torch.device("cuda" if device == "cuda" else "cpu")
    pipeline.to(torch_device)
    return pipeline


def _collect_turns(diarization_output) -> list[tuple[float, float, str]]:
    turns: list[tuple[float, float, str]] = []
    exclusive = getattr(diarization_output, "exclusive_speaker_diarization", None)
    if exclusive is not None:
        for turn, speaker in exclusive:
            turns.append((float(turn.start), float(turn.end), str(speaker)))
        return turns

    annotation = getattr(diarization_output, "speaker_diarization", diarization_output)
    if hasattr(annotation, "itertracks"):
        for turn, _, speaker in annotation.itertracks(yield_label=True):
            turns.append((float(turn.start), float(turn.end), str(speaker)))
        return turns

    for turn, speaker in annotation:
        turns.append((float(turn.start), float(turn.end), str(speaker)))
    return turns


def _speaker_for_interval(
    turns: list[tuple[float, float, str]], start: float, end: float
) -> str:
    best_speaker = "SPEAKER_UNKNOWN"
    best_overlap = 0.0
    for turn_start, turn_end, speaker in turns:
        overlap = max(0.0, min(end, turn_end) - max(start, turn_start))
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = speaker
    return best_speaker


def assign_speakers(
    audio_path: Path,
    segments: list[Any],
    *,
    device: str = "cpu",
    language: str | None = None,
) -> list[dict[str, Any]]:
    """Atribui rótulo de falante a cada segmento transcrito (pyannote offline após 1º download)."""
    del language  # reservado para extensões futuras
    if not is_pyannote_available():
        raise PyannoteNotAvailableError(install_hint())

    pipeline = _load_pipeline(device)
    diarization = pipeline(str(audio_path))
    turns = _collect_turns(diarization)

    labeled: list[dict[str, Any]] = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        speaker = _speaker_for_interval(turns, float(segment.start), float(segment.end))
        labeled.append(
            {
                "start": float(segment.start),
                "end": float(segment.end),
                "text": text,
                "speaker": speaker,
            }
        )
    return labeled
