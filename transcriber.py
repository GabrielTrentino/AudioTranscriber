import os
import sys
from collections.abc import Callable
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

MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
LANGUAGE = os.getenv("WHISPER_LANGUAGE", "pt")
# Pausa entre segmentos (segundos) para inserir linha em branco (novo parágrafo)
PAUSE_GAP_SECONDS = float(os.getenv("WHISPER_PAUSE_GAP", "1.5"))
# "none" | "line" (uma linha por segmento) | "time" ([00:01:23] texto)
OUTPUT_FORMAT = os.getenv("WHISPER_OUTPUT_FORMAT", "line").lower()

_MEMORY_PRESETS = {
    "low": {"cpu_threads": 2, "num_workers": 1, "chunk_length": 15, "beam_size": 1},
    "balanced": {"cpu_threads": 0, "num_workers": 1, "chunk_length": None, "beam_size": 5},
    "high": {"cpu_threads": 0, "num_workers": 1, "chunk_length": 30, "beam_size": 5},
}


def _optional_int_env(name: str) -> int | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return int(value)


def _load_memory_settings() -> dict:
    """Configura uso de RAM/CPU. Perfil + variáveis individuais (env sobrescreve perfil)."""
    profile = os.getenv("WHISPER_MEMORY_PROFILE", "balanced").strip().lower()
    if profile not in _MEMORY_PRESETS:
        profile = "balanced"

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

    beam_size = _optional_int_env("WHISPER_BEAM_SIZE")
    if beam_size is not None:
        settings["beam_size"] = beam_size

    return settings


MEMORY = _load_memory_settings()

_model: WhisperModel | None = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(
            MODEL_SIZE,
            device=DEVICE,
            compute_type=COMPUTE_TYPE,
            cpu_threads=MEMORY["cpu_threads"],
            num_workers=MEMORY["num_workers"],
        )
    return _model


def _format_timestamp(seconds: float) -> str:
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_segments(segments, output_format: str | None = None) -> str:
    """Monta o texto com quebras de linha entre falas/segmentos do Whisper."""
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


def transcribe_path(
    path: str | Path,
    *,
    include_timestamps: bool | None = None,
    on_progress: Callable[[float, str | None], None] | None = None,
) -> str:
    output_format = None
    if include_timestamps is True:
        output_format = "time"
    elif include_timestamps is False:
        output_format = "line"

    if on_progress:
        on_progress(0.0, "Carregando modelo…")

    model = get_model()

    if on_progress:
        on_progress(0.0, "Transcrevendo…")

    transcribe_kwargs: dict = {
        "language": LANGUAGE,
        "vad_filter": True,
        "beam_size": MEMORY["beam_size"],
    }
    if MEMORY["chunk_length"] is not None:
        transcribe_kwargs["chunk_length"] = MEMORY["chunk_length"]

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
    include_timestamps: bool = False,
    on_progress: Callable[[float, str | None], None] | None = None,
) -> Path:
    text = transcribe_path(
        input_path,
        include_timestamps=include_timestamps,
        on_progress=on_progress,
    )
    return save_transcription(input_path, output_dir, text, output_name)
