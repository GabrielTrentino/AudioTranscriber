"""Fila persistente de transcrições com retomada após interrupção."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from audiotranscriber.core.exceptions import TranscriptionCancelled
from audiotranscriber.core.settings import TranscriptionSettings
from audiotranscriber.services.transcription_service import TranscriptionService


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class QueueJob:
    id: str
    input_path: str
    output_dir: str
    status: str = JobStatus.PENDING.value
    output_file: str | None = None
    error: str | None = None
    updated_at: str = field(default_factory=lambda: _utc_now())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueueJob:
        return cls(
            id=data["id"],
            input_path=data["input_path"],
            output_dir=data["output_dir"],
            status=data.get("status", JobStatus.PENDING.value),
            output_file=data.get("output_file"),
            error=data.get("error"),
            updated_at=data.get("updated_at", _utc_now()),
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobQueueState:
    version: int = 1
    export_format: str = "txt"
    include_timestamps: bool = False
    jobs: list[QueueJob] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "export_format": self.export_format,
            "include_timestamps": self.include_timestamps,
            "jobs": [asdict(job) for job in self.jobs],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobQueueState:
        jobs = [QueueJob.from_dict(item) for item in data.get("jobs", [])]
        return cls(
            version=int(data.get("version", 1)),
            export_format=str(data.get("export_format", "txt")),
            include_timestamps=bool(data.get("include_timestamps", False)),
            jobs=jobs,
        )


class JobQueue:
    """Grava estado em JSON para retomar lotes longos."""

    def __init__(self, state_path: Path) -> None:
        self._path = state_path
        self.state = self._load()

    def _load(self) -> JobQueueState:
        if not self._path.is_file():
            return JobQueueState()
        with self._path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError(f"Estado inválido em {self._path}")
        return JobQueueState.from_dict(data)

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(self.state.to_dict(), handle, ensure_ascii=False, indent=2)

    def add_files(
        self,
        paths: list[Path],
        output_dir: Path | None,
        *,
        export_format: str = "txt",
        include_timestamps: bool = False,
    ) -> int:
        self.state.export_format = export_format
        self.state.include_timestamps = include_timestamps
        existing = {job.input_path for job in self.state.jobs}
        added = 0
        for path in paths:
            resolved = str(path.resolve())
            if resolved in existing:
                continue
            target = (
                str(output_dir.resolve())
                if output_dir is not None
                else str(path.resolve().parent)
            )
            self.state.jobs.append(
                QueueJob(
                    id=uuid.uuid4().hex[:12],
                    input_path=resolved,
                    output_dir=target,
                )
            )
            existing.add(resolved)
            added += 1
        self.save()
        return added

    def pending_jobs(self) -> list[QueueJob]:
        return [
            job
            for job in self.state.jobs
            if job.status in (JobStatus.PENDING.value, JobStatus.FAILED.value)
        ]

    def run(
        self,
        service: TranscriptionService,
        settings: TranscriptionSettings,
        *,
        on_progress: Callable[[float, str | None], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
        log: Callable[[str], None] | None = None,
    ) -> tuple[int, int, bool]:
        pending = self.pending_jobs()
        total = len(pending)
        done_count = 0
        failed_count = 0
        cancelled = False

        for index, job in enumerate(pending):
            if is_cancelled and is_cancelled():
                cancelled = True
                break

            job.status = JobStatus.RUNNING.value
            job.updated_at = _utc_now()
            self.save()

            input_path = Path(job.input_path)
            output_dir = Path(job.output_dir)

            def file_progress(
                ratio: float,
                message: str | None,
                *,
                idx=index,
            ) -> None:
                if on_progress is None:
                    return
                overall = (idx + max(0.0, min(ratio, 1.0))) / total if total else 1.0
                on_progress(overall, message or f"Arquivo {idx + 1}/{total}")

            try:
                if log:
                    log(f"transcrevendo {input_path.name}")
                out = service.transcribe_to_file(
                    input_path,
                    output_dir,
                    settings=settings,
                    include_timestamps=self.state.include_timestamps,
                    export_format=self.state.export_format,
                    on_progress=file_progress,
                    is_cancelled=is_cancelled,
                )
                job.status = JobStatus.DONE.value
                job.output_file = str(out)
                job.error = None
                done_count += 1
            except TranscriptionCancelled:
                job.status = JobStatus.PENDING.value
                cancelled = True
            except Exception as exc:
                job.status = JobStatus.FAILED.value
                job.error = str(exc)
                failed_count += 1
                if log:
                    log(f"erro {input_path.name}: {exc}")

            job.updated_at = _utc_now()
            self.save()

            if cancelled:
                break

        return done_count, failed_count, cancelled
