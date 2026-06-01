"""Configuração unificada: variáveis de ambiente e config.yaml opcional."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment,misc]


def _app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # src/audiotranscriber/config -> repo root (AudioTranscriber/)
    return Path(__file__).resolve().parents[3]


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


@dataclass
class AppConfig:
    device: str = "cpu"
    pause_gap_seconds: float = 1.5
    output_format: str = "line"
    default_language: str = "pt"
    default_model: str = "base"
    default_compute_type: str = "int8"
    default_memory_profile: str = "balanced"
    default_quality_preset: str = "equilibrada"
    cpu_threads: int | None = None
    num_workers: int | None = None
    chunk_length: int | None = None
    beam_size: int | None = None

    @classmethod
    def from_sources(cls, yaml_path: Path | None = None) -> AppConfig:
        data: dict = {}
        path = yaml_path or (_app_root() / "config.yaml")
        if path.is_file() and yaml is not None:
            with path.open(encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle)
                if isinstance(loaded, dict):
                    data = loaded

        def env_or_yaml(env_key: str, yaml_key: str, default: object) -> object:
            env_val = os.getenv(env_key)
            if env_val is not None and str(env_val).strip() != "":
                return env_val
            if yaml_key in data and data[yaml_key] is not None:
                return data[yaml_key]
            return default

        pause = env_or_yaml("WHISPER_PAUSE_GAP", "pause_gap_seconds", 1.5)
        return cls(
            device=str(env_or_yaml("WHISPER_DEVICE", "device", "cpu")),
            pause_gap_seconds=float(pause),
            output_format=str(
                env_or_yaml("WHISPER_OUTPUT_FORMAT", "output_format", "line")
            ).lower(),
            default_language=str(
                env_or_yaml("WHISPER_LANGUAGE", "default_language", "pt")
            ),
            default_model=str(
                env_or_yaml("WHISPER_MODEL", "default_model", "base")
            ),
            default_compute_type=str(
                env_or_yaml("WHISPER_COMPUTE_TYPE", "default_compute_type", "int8")
            ),
            default_memory_profile=str(
                env_or_yaml(
                    "WHISPER_MEMORY_PROFILE", "default_memory_profile", "balanced"
                )
            ),
            default_quality_preset=str(
                env_or_yaml(
                    "WHISPER_QUALITY_PRESET", "default_quality_preset", "equilibrada"
                )
            ),
            cpu_threads=_optional_int(
                env_or_yaml("WHISPER_CPU_THREADS", "cpu_threads", None)
            ),
            num_workers=_optional_int(
                env_or_yaml("WHISPER_NUM_WORKERS", "num_workers", None)
            ),
            chunk_length=_optional_int(
                env_or_yaml("WHISPER_CHUNK_LENGTH", "chunk_length", None)
            ),
            beam_size=_optional_int(
                env_or_yaml("WHISPER_BEAM_SIZE", "beam_size", None)
            ),
        )


_config: AppConfig | None = None


def get_app_config() -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig.from_sources()
    return _config
