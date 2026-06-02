"""Diarização via WhisperX (usa pyannote por baixo) — extra pip diarization-whisperx."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from audiotranscriber.services.diarization_common import (
    hf_token,
    normalize_speaker_labels,
)


class DiarizationNotAvailableError(ImportError):
    """WhisperX não instalado ou token HF ausente."""


def is_whisperx_installed() -> bool:
    try:
        import whisperx  # noqa: F401

        return True
    except ImportError:
        return False


def is_whisperx_diarization_ready() -> bool:
    return is_whisperx_installed() and hf_token() is not None


def is_diarization_available() -> bool:
    return is_whisperx_diarization_ready()


def diarization_install_hint() -> str:
    return (
        "Instale: pip install \"audiotranscriber[diarization-whisperx]\"\n"
        "Aceite os termos em https://huggingface.co/pyannote/speaker-diarization-community-1\n"
        "Defina HF_TOKEN com token de leitura do Hugging Face."
    )


def assign_speakers(
    audio_path: Path,
    segments: list[Any],
    *,
    device: str = "cpu",
    language: str | None = None,
) -> list[dict[str, Any]]:
    """
    Atribui rótulos de falante aos segmentos usando WhisperX DiarizationPipeline.

    Retorna lista de dicts com start, end, text e speaker.
    """
    if not is_whisperx_installed():
        raise DiarizationNotAvailableError(diarization_install_hint())

    token = hf_token()
    if not token:
        raise DiarizationNotAvailableError(
            "Token Hugging Face ausente. Defina HF_TOKEN.\n" + diarization_install_hint()
        )

    import whisperx

    audio = whisperx.load_audio(str(audio_path))

    diarize_model = whisperx.DiarizationPipeline(token=token, device=device)
    diarize_segments = diarize_model(audio)

    segment_dicts = [
        {"start": float(s.start), "end": float(s.end), "text": s.text.strip()}
        for s in segments
        if s.text and s.text.strip()
    ]
    aligned = whisperx.assign_word_speakers(
        diarize_segments, {"segments": segment_dicts}
    )
    result: list[dict[str, Any]] = []
    for item in aligned.get("segments", segment_dicts):
        text = item.get("text", "").strip()
        if not text:
            continue
        result.append(
            {
                "start": float(item["start"]),
                "end": float(item["end"]),
                "text": text,
                "speaker": item.get("speaker", "SPEAKER_UNKNOWN"),
            }
        )
    return normalize_speaker_labels(result)


def format_segments_with_speakers(
    segments: list[dict[str, Any]],
    *,
    include_timestamps: bool = False,
    pause_gap: float | None = None,
) -> str:
    from audiotranscriber.core.formatter import format_labeled_segments

    return format_labeled_segments(
        segments,
        include_timestamps=include_timestamps,
        pause_gap=pause_gap,
    )
