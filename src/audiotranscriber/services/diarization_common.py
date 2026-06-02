"""Utilitários compartilhados para diarização (token HF, atribuição de falantes)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


def _project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def _read_secrets_env() -> dict[str, str]:
    env_path = _project_root() / "secrets" / ".env"
    if not env_path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, raw = line.partition("=")
        key = key.strip()
        value = raw.strip().strip('"').strip("'")
        if key and value:
            values[key] = value
    return values


def hf_token() -> str | None:
    for key in ("HF_TOKEN", "HUGGINGFACE_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    file_values = _read_secrets_env()
    for key in ("HF_TOKEN", "HUGGINGFACE_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        value = file_values.get(key, "").strip()
        if value:
            return value
    return None


def diarization_model_id() -> str:
    return os.getenv(
        "DIARIZATION_MODEL",
        "pyannote/speaker-diarization-community-1",
    ).strip()


def diarization_speaker_count_options() -> dict[str, int | None]:
    """Lê num/min/max de falantes do ambiente (opcional)."""

    def _read(name: str) -> int | None:
        raw = os.getenv(name, "").strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    return {
        "num_speakers": _read("DIARIZATION_NUM_SPEAKERS"),
        "min_speakers": _read("DIARIZATION_MIN_SPEAKERS"),
        "max_speakers": _read("DIARIZATION_MAX_SPEAKERS"),
    }


class _IntervalTree:
    """Consulta de sobreposição temporal (O(log n) por segmento)."""

    def __init__(self, intervals: list[tuple[float, float, str]]) -> None:
        if not intervals:
            self._starts: list[float] = []
            self._ends: list[float] = []
            self._speakers: list[str] = []
            return
        ordered = sorted(intervals, key=lambda item: item[0])
        self._starts = [item[0] for item in ordered]
        self._ends = [item[1] for item in ordered]
        self._speakers = [item[2] for item in ordered]

    def query(self, start: float, end: float) -> list[tuple[str, float]]:
        if not self._starts:
            return []
        results: list[tuple[str, float]] = []
        for idx, seg_start in enumerate(self._starts):
            seg_end = self._ends[idx]
            if seg_start >= end:
                break
            if seg_end <= start:
                continue
            overlap = min(seg_end, end) - max(seg_start, start)
            if overlap > 0:
                results.append((self._speakers[idx], overlap))
        return results

    def find_nearest(self, time: float) -> str | None:
        if not self._starts:
            return None
        best_idx = 0
        best_dist = float("inf")
        for idx, seg_start in enumerate(self._starts):
            mid = (seg_start + self._ends[idx]) / 2
            dist = abs(mid - time)
            if dist < best_dist:
                best_dist = dist
                best_idx = idx
        return self._speakers[best_idx]


def collect_pyannote_turns(diarization_output) -> list[tuple[float, float, str]]:
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

    if hasattr(annotation, "__iter__"):
        for turn, speaker in annotation:
            turns.append((float(turn.start), float(turn.end), str(speaker)))
    return turns


def assign_speakers_to_segments(
    turns: list[tuple[float, float, str]],
    segments: list[Any],
    *,
    fill_nearest: bool = True,
) -> list[dict[str, Any]]:
    tree = _IntervalTree(turns)
    labeled: list[dict[str, Any]] = []

    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        start = float(segment.start)
        end = float(segment.end)
        overlaps = tree.query(start, end)
        speaker = "SPEAKER_UNKNOWN"
        if overlaps:
            totals: dict[str, float] = {}
            for spk, duration in overlaps:
                totals[spk] = totals.get(spk, 0.0) + duration
            speaker = max(totals.items(), key=lambda item: item[1])[0]
        elif fill_nearest:
            nearest = tree.find_nearest((start + end) / 2)
            if nearest:
                speaker = nearest

        labeled.append(
            {
                "start": start,
                "end": end,
                "text": text,
                "speaker": speaker,
            }
        )
    return labeled


def normalize_speaker_labels(
    labeled: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Mapeia rótulos do pyannote para SPEAKER_00, SPEAKER_01, … por ordem de aparição."""
    mapping: dict[str, str] = {}
    counter = 0
    for item in labeled:
        raw = str(item.get("speaker", "SPEAKER_UNKNOWN"))
        if raw not in mapping:
            mapping[raw] = f"SPEAKER_{counter:02d}"
            counter += 1
        item["speaker"] = mapping[raw]
    return labeled
