"""Diarização opcional (WhisperX) — extra pip install audiotranscriber[diarization]."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class DiarizationNotAvailableError(ImportError):
    """WhisperX não instalado."""


def is_diarization_available() -> bool:
    try:
        import whisperx  # noqa: F401

        return True
    except ImportError:
        return False


def diarization_install_hint() -> str:
    return "Instale o extra: pip install 'audiotranscriber[diarization]'"


def assign_speakers(
    audio_path: Path,
    segments: list[Any],
    *,
    device: str = "cpu",
    language: str | None = None,
) -> list[dict[str, Any]]:
    """
    Atribui rótulos de falante aos segmentos usando WhisperX.

    Retorna lista de dicts com start, end, text e speaker.
    """
    if not is_diarization_available():
        raise DiarizationNotAvailableError(diarization_install_hint())

    import whisperx

    audio = whisperx.load_audio(str(audio_path))
    lang = language or "pt"

    diarize_model = whisperx.DiarizationPipeline(device=device)
    diarize_segments = diarize_model(audio)

    segment_dicts = [
        {"start": float(s.start), "end": float(s.end), "text": s.text.strip()}
        for s in segments
        if s.text and s.text.strip()
    ]
    aligned = whisperx.assign_word_speakers(diarize_segments, {"segments": segment_dicts})
    result: list[dict[str, Any]] = []
    for item in aligned.get("segments", segment_dicts):
        speaker = item.get("speaker", "SPEAKER")
        text = item.get("text", "").strip()
        if not text:
            continue
        result.append(
            {
                "start": float(item["start"]),
                "end": float(item["end"]),
                "text": text,
                "speaker": speaker,
            }
        )
    return result


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
