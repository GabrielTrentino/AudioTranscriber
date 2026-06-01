import os
import sys
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

_model: WhisperModel | None = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    return _model


def _format_timestamp(seconds: float) -> str:
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_segments(segments) -> str:
    """Monta o texto com quebras de linha entre falas/segmentos do Whisper."""
    if OUTPUT_FORMAT == "none":
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

        if OUTPUT_FORMAT == "time":
            lines.append(f"[{_format_timestamp(segment.start)}] {text}")
        else:
            lines.append(text)

        prev_end = segment.end

    return "\n".join(lines).strip()


def transcribe_path(path: str | Path) -> str:
    segments, _ = get_model().transcribe(
        str(path),
        language=LANGUAGE,
        vad_filter=True,
    )
    return format_segments(segments)


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
) -> Path:
    text = transcribe_path(input_path)
    return save_transcription(input_path, output_dir, text, output_name)
