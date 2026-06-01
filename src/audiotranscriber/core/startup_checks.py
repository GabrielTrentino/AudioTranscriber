"""Verificações de ambiente no startup (GUI / .exe)."""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StartupIssue:
    level: str  # "error" | "warning"
    message: str


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def find_ffmpeg() -> Path | None:
    local = _app_dir() / "ffmpeg.exe"
    if local.is_file():
        return local
    found = shutil.which("ffmpeg")
    return Path(found) if found else None


def check_writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def run_startup_checks() -> list[StartupIssue]:
    issues: list[StartupIssue] = []

    if find_ffmpeg() is None:
        issues.append(
            StartupIssue(
                level="error",
                message=(
                    "FFmpeg não encontrado. Coloque ffmpeg.exe na pasta do programa "
                    "ou instale FFmpeg no PATH."
                ),
            )
        )

    log_dir = _app_dir()
    if not check_writable_dir(log_dir):
        fallback = Path.home() / "AudioTranscriber"
        if not check_writable_dir(fallback):
            issues.append(
                StartupIssue(
                    level="warning",
                    message=(
                        f"Não foi possível gravar logs em {log_dir} nem em {fallback}."
                    ),
                )
            )

    if getattr(sys, "frozen", False):
        internal = _app_dir() / "_internal"
        python_dll = list(internal.glob("python3*.dll")) if internal.is_dir() else []
        if not python_dll:
            issues.append(
                StartupIssue(
                    level="warning",
                    message=(
                        "Build pode estar incompleto (python3*.dll ausente em _internal). "
                        "Reinstale o Visual C++ Redistributable se o app não abrir."
                    ),
                )
            )

    return issues


def format_issues(issues: list[StartupIssue]) -> str:
    lines = []
    for issue in issues:
        prefix = "ERRO" if issue.level == "error" else "Aviso"
        lines.append(f"{prefix}: {issue.message}")
    return "\n\n".join(lines)


def has_blocking_errors(issues: list[StartupIssue]) -> bool:
    return any(issue.level == "error" for issue in issues)
