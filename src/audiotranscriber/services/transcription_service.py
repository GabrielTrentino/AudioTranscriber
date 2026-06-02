from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from audiotranscriber.core.exceptions import TranscriptionCancelled
from audiotranscriber.core.exporters import format_export
from audiotranscriber.core.formatter import format_segments
from audiotranscriber.core.formatter import format_labeled_segments
from audiotranscriber.services.diarization_backend import (
    assign_speaker_labels,
    diarization_install_hint,
    is_diarization_available,
)
from audiotranscriber.core.memory import resolve_memory_settings
from audiotranscriber.core.speaker_names import (
    load_speaker_names,
    mapping_from_labeled,
    speakers_sidecar_path,
    write_speaker_names,
)
from audiotranscriber.core.model_manager import ModelManager, get_model_manager
from audiotranscriber.core.settings import TranscriptionSettings


def _check_cancelled(is_cancelled: Callable[[], bool] | None) -> None:
    if is_cancelled and is_cancelled():
        raise TranscriptionCancelled("Transcrição cancelada pelo usuário.")


def _resolve_language(language: str) -> str | None:
    lang = language.strip().lower()
    if not lang or lang == "auto":
        return None
    return language.strip()


def resolve_output_filename(
    name: str | None,
    input_path: Path,
    export_format: str = "txt",
) -> str:
    ext = _extension_for_format(export_format)
    if not name or not name.strip():
        return f"{input_path.stem}{ext}"

    filename = name.strip()
    lower = filename.lower()
    known = (".txt", ".srt", ".vtt", ".json")
    if not any(lower.endswith(suffix) for suffix in known):
        filename = f"{filename}{ext}"

    for char in '<>:"/\\|?*':
        filename = filename.replace(char, "_")
    return filename


def _extension_for_format(export_format: str) -> str:
    fmt = export_format.lower()
    if fmt == "srt":
        return ".srt"
    if fmt == "vtt":
        return ".vtt"
    if fmt == "json":
        return ".json"
    return ".txt"


@dataclass
class TranscriptionResult:
    text: str
    labeled_segments: list[dict] | None = None


class TranscriptionService:
    """Orquestra carregamento do modelo, transcrição e gravação."""

    def __init__(self, model_manager: ModelManager | None = None) -> None:
        self._models = model_manager or get_model_manager()

    @property
    def device(self) -> str:
        return self._models.device

    def transcribe_path(
        self,
        path: str | Path,
        *,
        settings: TranscriptionSettings | None = None,
        include_timestamps: bool | None = None,
        export_format: str = "txt",
        diarize: bool = False,
        speaker_name_map: dict[str, str] | None = None,
        on_progress: Callable[[float, str | None], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> TranscriptionResult:
        cfg = settings or TranscriptionSettings.from_env()
        fmt = export_format.lower()

        output_format = None
        if fmt == "txt":
            if include_timestamps is True:
                output_format = "time"
            elif include_timestamps is False:
                output_format = "line"

        _check_cancelled(is_cancelled)

        if on_progress:
            on_progress(0.0, "loading")

        model = self._models.get_model(cfg)
        _check_cancelled(is_cancelled)
        memory = resolve_memory_settings(cfg.memory_profile, beam_size=cfg.beam_size)

        if on_progress:
            on_progress(0.0, "transcribing")

        transcribe_kwargs: dict = {
            "language": _resolve_language(cfg.language),
            "vad_filter": True,
            "beam_size": memory["beam_size"],
            "condition_on_previous_text": True,
        }
        if memory["chunk_length"] is not None:
            transcribe_kwargs["chunk_length"] = memory["chunk_length"]

        segments, info = model.transcribe(str(path), **transcribe_kwargs)
        duration = getattr(info, "duration", None) or 0.0

        collected = []
        last_reported_pct = -1
        for segment in segments:
            _check_cancelled(is_cancelled)
            collected.append(segment)
            if on_progress:
                if duration > 0:
                    ratio = min(segment.end / duration, 0.99)
                    pct = int(ratio * 100)
                    if pct != last_reported_pct:
                        last_reported_pct = pct
                        on_progress(ratio, None)
                elif last_reported_pct < 0:
                    last_reported_pct = 0
                    on_progress(0.0, None)

        if diarize:
            if not is_diarization_available():
                raise RuntimeError(diarization_install_hint())
            if on_progress:
                on_progress(0.99, "diarizing")
            lang = _resolve_language(cfg.language)
            labeled = assign_speaker_labels(
                Path(path),
                collected,
                device=self.device,
                language=lang,
            )
            if fmt == "json":
                import json

                return TranscriptionResult(
                    text=json.dumps(labeled, ensure_ascii=False, indent=2),
                    labeled_segments=labeled,
                )
            with_timestamps = include_timestamps is True
            return TranscriptionResult(
                text=format_labeled_segments(
                    labeled,
                    include_timestamps=with_timestamps,
                    speaker_names=speaker_name_map,
                ),
                labeled_segments=labeled,
            )

        if on_progress:
            on_progress(1.0, "saving")

        if fmt in ("srt", "vtt", "json"):
            return TranscriptionResult(text=format_export(collected, fmt))
        return TranscriptionResult(
            text=format_segments(collected, output_format)
        )

    def save_transcription(
        self,
        input_path: Path,
        output_dir: Path,
        text: str,
        output_name: str | None = None,
        export_format: str = "txt",
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / resolve_output_filename(
            output_name, input_path, export_format
        )
        output_file.write_text(text, encoding="utf-8")
        return output_file

    def transcribe_to_file(
        self,
        input_path: Path,
        output_dir: Path,
        output_name: str | None = None,
        *,
        settings: TranscriptionSettings | None = None,
        include_timestamps: bool = False,
        export_format: str = "txt",
        diarize: bool = False,
        on_progress: Callable[[float, str | None], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / resolve_output_filename(
            output_name, input_path, export_format
        )
        sidecar = speakers_sidecar_path(output_file)
        name_map = load_speaker_names(sidecar) if diarize else {}

        result = self.transcribe_path(
            input_path,
            settings=settings,
            include_timestamps=include_timestamps,
            export_format=export_format,
            diarize=diarize,
            speaker_name_map=name_map or None,
            on_progress=on_progress,
            is_cancelled=is_cancelled,
        )
        output_file.write_text(result.text, encoding="utf-8")
        if diarize and result.labeled_segments:
            write_speaker_names(
                sidecar,
                mapping_from_labeled(result.labeled_segments, name_map),
            )
        return output_file
