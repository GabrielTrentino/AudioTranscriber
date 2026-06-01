import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from faster_whisper import WhisperModel


def _setup_ffmpeg_path() -> None:
    """Permite colocar ffmpeg.exe na pasta do .exe (distribuição empacotada)."""
    if getattr(sys, "frozen", False):
        app_dir = Path(sys.executable).resolve().parent
    else:
        app_dir = Path(__file__).resolve().parent

    if (app_dir / "ffmpeg.exe").is_file():
        os.environ["PATH"] = str(app_dir) + os.pathsep + os.environ.get("PATH", "")


_setup_ffmpeg_path()

DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
PAUSE_GAP_SECONDS = float(os.getenv("WHISPER_PAUSE_GAP", "1.5"))
OUTPUT_FORMAT = os.getenv("WHISPER_OUTPUT_FORMAT", "line").lower()

MODEL_OPTIONS = ("tiny", "base", "small", "medium", "large-v3")
COMPUTE_OPTIONS = ("int8", "float16", "float32")
MEMORY_PROFILE_OPTIONS = ("low", "balanced", "high")
QUALITY_PRESET_OPTIONS = ("rapida", "equilibrada", "alta", "personalizado")

_MEMORY_PRESETS = {
    "low": {"cpu_threads": 2, "num_workers": 1, "chunk_length": 15, "beam_size": 1},
    "balanced": {"cpu_threads": 0, "num_workers": 1, "chunk_length": None, "beam_size": 5},
    "high": {"cpu_threads": 0, "num_workers": 1, "chunk_length": 30, "beam_size": 5},
}

_model: WhisperModel | None = None
_model_cache_key: tuple | None = None


def _optional_int_env(name: str) -> int | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return int(value)


def resolve_memory_settings(
    profile: str,
    *,
    beam_size: int | None = None,
) -> dict:
    profile = profile if profile in _MEMORY_PRESETS else "balanced"
    settings = dict(_MEMORY_PRESETS[profile])

    cpu_threads = _optional_int_env("WHISPER_CPU_THREADS")
    if cpu_threads is not None:
        settings["cpu_threads"] = cpu_threads

    num_workers = _optional_int_env("WHISPER_NUM_WORKERS")
    if num_workers is not None:
        settings["num_workers"] = num_workers

    chunk_length = _optional_int_env("WHISPER_CHUNK_LENGTH")
    if chunk_length is not None:
        settings["chunk_length"] = chunk_length

    env_beam = _optional_int_env("WHISPER_BEAM_SIZE")
    if beam_size is not None:
        settings["beam_size"] = beam_size
    elif env_beam is not None:
        settings["beam_size"] = env_beam

    return settings


@dataclass
class TranscriptionSettings:
    model_size: str = "base"
    compute_type: str = "int8"
    memory_profile: str = "balanced"
    language: str = "pt"
    beam_size: int | None = None
    quality_preset: str = "equilibrada"

    @classmethod
    def from_env(cls) -> "TranscriptionSettings":
        preset = os.getenv("WHISPER_QUALITY_PRESET", "").strip().lower()
        if preset in ("rapida", "equilibrada", "alta"):
            return cls.from_quality_preset(preset)

        return cls(
            model_size=os.getenv("WHISPER_MODEL", "base"),
            compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
            memory_profile=os.getenv("WHISPER_MEMORY_PROFILE", "balanced"),
            language=os.getenv("WHISPER_LANGUAGE", "pt"),
            beam_size=_optional_int_env("WHISPER_BEAM_SIZE"),
            quality_preset="personalizado",
        )

    @classmethod
    def from_quality_preset(cls, preset: str) -> "TranscriptionSettings":
        presets = {
            "rapida": cls(
                model_size="base",
                memory_profile="low",
                beam_size=1,
                compute_type="int8",
                quality_preset="rapida",
            ),
            "equilibrada": cls(
                model_size="base",
                memory_profile="balanced",
                beam_size=5,
                compute_type="int8",
                quality_preset="equilibrada",
            ),
            "alta": cls(
                model_size="small",
                memory_profile="high",
                beam_size=5,
                compute_type="int8",
                quality_preset="alta",
            ),
        }
        return presets.get(preset, presets["equilibrada"])


def get_model(settings: TranscriptionSettings) -> WhisperModel:
    global _model, _model_cache_key
    memory = resolve_memory_settings(
        settings.memory_profile,
        beam_size=settings.beam_size,
    )
    cache_key = (
        settings.model_size,
        DEVICE,
        settings.compute_type,
        memory["cpu_threads"],
        memory["num_workers"],
    )

    if _model is None or _model_cache_key != cache_key:
        _model = WhisperModel(
            settings.model_size,
            device=DEVICE,
            compute_type=settings.compute_type,
            cpu_threads=memory["cpu_threads"],
            num_workers=memory["num_workers"],
        )
        _model_cache_key = cache_key

    return _model


def _format_timestamp(seconds: float) -> str:
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_segments(segments, output_format: str | None = None) -> str:
    fmt = (output_format or OUTPUT_FORMAT).lower()

    if fmt == "none":
        return "".join(segment.text for segment in segments).strip()

    lines: list[str] = []
    prev_end: float | None = None

    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue

        if (
            prev_end is not None
            and segment.start - prev_end >= PAUSE_GAP_SECONDS
        ):
            lines.append("")

        if fmt == "time":
            start = _format_timestamp(segment.start)
            end = _format_timestamp(segment.end)
            lines.append(f"[{start} - {end}] {text}")
        else:
            lines.append(text)

        prev_end = segment.end

    return "\n".join(lines).strip()


def _resolve_language(language: str) -> str | None:
    lang = language.strip().lower()
    if not lang or lang == "auto":
        return None
    return language.strip()


def transcribe_path(
    path: str | Path,
    *,
    settings: TranscriptionSettings | None = None,
    include_timestamps: bool | None = None,
    on_progress: Callable[[float, str | None], None] | None = None,
) -> str:
    cfg = settings or TranscriptionSettings.from_env()

    output_format = None
    if include_timestamps is True:
        output_format = "time"
    elif include_timestamps is False:
        output_format = "line"

    if on_progress:
        on_progress(0.0, f"Carregando modelo {cfg.model_size}…")

    model = get_model(cfg)
    memory = resolve_memory_settings(cfg.memory_profile, beam_size=cfg.beam_size)

    if on_progress:
        on_progress(0.0, "Transcrevendo…")

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
    for segment in segments:
        collected.append(segment)
        if on_progress:
            if duration > 0:
                ratio = min(segment.end / duration, 0.99)
                on_progress(ratio, f"Transcrevendo… {int(ratio * 100)}%")
            else:
                on_progress(-1.0, "Transcrevendo…")

    if on_progress:
        on_progress(1.0, "Salvando arquivo…")

    return format_segments(collected, output_format)


def resolve_output_filename(name: str | None, input_path: Path) -> str:
    if not name or not name.strip():
        return f"{input_path.stem}.txt"

    filename = name.strip()
    if not filename.lower().endswith(".txt"):
        filename = f"{filename}.txt"

    for char in '<>:"/\\|?*':
        filename = filename.replace(char, "_")
    return filename


def save_transcription(
    input_path: Path,
    output_dir: Path,
    text: str,
    output_name: str | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / resolve_output_filename(output_name, input_path)
    output_file.write_text(text, encoding="utf-8")
    return output_file


def transcribe_to_file(
    input_path: Path,
    output_dir: Path,
    output_name: str | None = None,
    *,
    settings: TranscriptionSettings | None = None,
    include_timestamps: bool = False,
    on_progress: Callable[[float, str | None], None] | None = None,
) -> Path:
    text = transcribe_path(
        input_path,
        settings=settings,
        include_timestamps=include_timestamps,
        on_progress=on_progress,
    )
    return save_transcription(input_path, output_dir, text, output_name)
