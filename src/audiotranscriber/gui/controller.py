"""Orquestra jobs de transcrição sem dependência de tkinter."""

from __future__ import annotations

import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from audiotranscriber.core.exceptions import TranscriptionCancelled
from audiotranscriber.core.settings import TranscriptionSettings
from audiotranscriber.services import TranscriptionService


@dataclass
class QualityFormState:
    quality_preset_label: str
    quality_labels: dict[str, str]
    model_size: str
    memory_profile: str
    compute_type: str
    beam_size: str
    language: str

    def build_settings(self) -> TranscriptionSettings:
        preset_key = self.quality_labels.get(
            self.quality_preset_label, "equilibrada"
        )
        if preset_key != "personalizado":
            settings = TranscriptionSettings.from_quality_preset(preset_key)
            settings.language = self.language
            return settings

        return TranscriptionSettings(
            model_size=self.model_size,
            compute_type=self.compute_type,
            memory_profile=self.memory_profile,
            language=self.language,
            beam_size=int(self.beam_size),
            quality_preset="personalizado",
        )


class TranscriptionController:
    def __init__(self, service: TranscriptionService | None = None) -> None:
        self._service = service or TranscriptionService()

    @property
    def device(self) -> str:
        return self._service.device

    def output_dir_for_input(
        self, input_path: Path, explicit_output_dir: str
    ) -> Path:
        if explicit_output_dir.strip():
            return Path(explicit_output_dir.strip())
        return input_path.resolve().parent

    def run_single(
        self,
        input_path: Path,
        output_dir: Path,
        output_name: str | None,
        settings: TranscriptionSettings,
        include_timestamps: bool,
        identify_speakers: bool = False,
        *,
        on_progress: Callable[[float, str | None], None],
        is_cancelled: Callable[[], bool],
        log: Callable[[str], None],
    ) -> Path:
        on_progress(0.0, "preparing")
        log(f"transcribe {input_path.name} -> {output_dir}")
        if identify_speakers:
            log("identificação de falantes ativada")
        try:
            output_file = self._service.transcribe_to_file(
                input_path,
                output_dir,
                output_name,
                settings=settings,
                include_timestamps=include_timestamps,
                diarize=identify_speakers,
                on_progress=on_progress,
                is_cancelled=is_cancelled,
            )
            log(f"done {output_file}")
            return output_file
        except TranscriptionCancelled:
            log("cancelled")
            raise
        except Exception as exc:
            log(f"error\n{exc}\n\n{traceback.format_exc()}")
            raise

    def run_batch(
        self,
        paths: list[Path],
        output_dir: Path | None,
        use_input_folder: bool,
        settings: TranscriptionSettings,
        include_timestamps: bool,
        identify_speakers: bool = False,
        *,
        on_progress: Callable[[float, str | None], None],
        is_cancelled: Callable[[], bool],
        log: Callable[[str], None],
    ) -> tuple[list[Path], list[str], bool]:
        total = len(paths)
        saved: list[Path] = []
        errors: list[str] = []
        cancelled = False

        for index, input_path in enumerate(paths):
            if is_cancelled():
                cancelled = True
                break

            file_label = input_path.name

            def file_progress(
                ratio: float,
                message: str | None,
                *,
                idx=index,
                label=file_label,
            ) -> None:
                overall = (idx + max(0.0, min(ratio, 1.0))) / total
                pct = int(max(0.0, min(ratio, 1.0)) * 100)
                on_progress(
                    overall,
                    f"Arquivo {idx + 1}/{total}: {label} — {pct}%",
                )

            try:
                target_dir = (
                    input_path.resolve().parent if use_input_folder else output_dir
                )
                output_file = self._service.transcribe_to_file(
                    input_path,
                    target_dir,
                    output_name=None,
                    settings=settings,
                    include_timestamps=include_timestamps,
                    diarize=identify_speakers,
                    on_progress=file_progress,
                    is_cancelled=is_cancelled,
                )
                saved.append(output_file)
            except TranscriptionCancelled:
                cancelled = True
                break
            except Exception as exc:
                errors.append(f"{file_label}: {exc}")

        if cancelled:
            log("batch cancelled")
        return saved, errors, cancelled
