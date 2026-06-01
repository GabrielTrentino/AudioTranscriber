"""Exportação de segmentos para SRT, VTT e JSON."""

from __future__ import annotations

import json
from typing import Any


def _srt_timestamp(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def _vtt_timestamp(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"
    return f"{minutes:02d}:{secs:02d}.{ms:03d}"


def segments_to_dicts(segments) -> list[dict[str, Any]]:
    return [
        {
            "start": float(segment.start),
            "end": float(segment.end),
            "text": segment.text.strip(),
        }
        for segment in segments
        if segment.text and segment.text.strip()
    ]


def format_srt(segments) -> str:
    blocks: list[str] = []
    for index, segment in enumerate(segments, start=1):
        text = segment.text.strip()
        if not text:
            continue
        start = _srt_timestamp(segment.start)
        end = _srt_timestamp(segment.end)
        blocks.append(f"{index}\n{start} --> {end}\n{text}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def format_vtt(segments) -> str:
    lines = ["WEBVTT", ""]
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        start = _vtt_timestamp(segment.start)
        end = _vtt_timestamp(segment.end)
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def format_json(segments) -> str:
    return json.dumps(segments_to_dicts(segments), ensure_ascii=False, indent=2)


def format_export(segments, export_format: str) -> str:
    fmt = export_format.lower()
    if fmt == "srt":
        return format_srt(segments)
    if fmt == "vtt":
        return format_vtt(segments)
    if fmt == "json":
        return format_json(segments)
    raise ValueError(f"Formato de exportação desconhecido: {export_format}")
