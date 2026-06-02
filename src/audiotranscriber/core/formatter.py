from audiotranscriber.config import get_app_config
from audiotranscriber.core.speaker_names import display_speaker


def _format_timestamp(seconds: float) -> str:
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_segments(segments, output_format: str | None = None) -> str:
    cfg = get_app_config()
    fmt = (output_format or cfg.output_format).lower()
    pause_gap = cfg.pause_gap_seconds

    if fmt == "none":
        return "".join(segment.text for segment in segments).strip()

    lines: list[str] = []
    prev_end: float | None = None

    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue

        if prev_end is not None and segment.start - prev_end >= pause_gap:
            lines.append("")

        if fmt == "time":
            start = _format_timestamp(segment.start)
            end = _format_timestamp(segment.end)
            lines.append(f"[{start} - {end}] {text}")
        else:
            lines.append(text)

        prev_end = segment.end

    return "\n".join(lines).strip()


def format_labeled_segments(
    segments: list[dict],
    *,
    include_timestamps: bool = False,
    pause_gap: float | None = None,
    speaker_names: dict[str, str] | None = None,
) -> str:
    """Formata trechos com falante e, opcionalmente, intervalo de tempo."""
    cfg = get_app_config()
    gap = pause_gap if pause_gap is not None else cfg.pause_gap_seconds

    lines: list[str] = []
    prev_end: float | None = None

    for item in segments:
        text = item.get("text", "").strip()
        if not text:
            continue

        start = float(item["start"])
        end = float(item["end"])
        speaker = display_speaker(
            str(item.get("speaker", "SPEAKER")), speaker_names
        )

        if prev_end is not None and start - prev_end >= gap:
            lines.append("")

        if include_timestamps:
            t0 = _format_timestamp(start)
            t1 = _format_timestamp(end)
            lines.append(f"[{speaker}] [{t0} - {t1}] {text}")
        else:
            lines.append(f"[{speaker}] {text}")

        prev_end = end

    return "\n".join(lines).strip()
