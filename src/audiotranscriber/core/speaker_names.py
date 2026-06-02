"""Mapeamento SPEAKER_XX → nome exibido (sidecar .speakers.json)."""

from __future__ import annotations

import json
from pathlib import Path


def speakers_sidecar_path(output_file: Path) -> Path:
    return output_file.with_name(f"{output_file.stem}.speakers.json")


def load_speaker_names(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value).strip() for key, value in data.items()}


def write_speaker_names(path: Path, mapping: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def mapping_from_labeled(
    labeled: list[dict],
    existing: dict[str, str] | None = None,
) -> dict[str, str]:
    """Preserva nomes já preenchidos; adiciona falantes novos com valor vazio."""
    result = dict(existing or {})
    for item in labeled:
        speaker = str(item.get("speaker", "")).strip()
        if not speaker:
            continue
        if speaker not in result:
            result[speaker] = ""
    return result


def display_speaker(speaker_id: str, mapping: dict[str, str] | None) -> str:
    if not mapping:
        return speaker_id
    name = mapping.get(speaker_id, "").strip()
    return name if name else speaker_id
