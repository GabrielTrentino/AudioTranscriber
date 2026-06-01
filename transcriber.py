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

_model: WhisperModel | None = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    return _model


def transcribe_path(path: str | Path) -> str:
    segments, _ = get_model().transcribe(str(path), language=LANGUAGE)
    return "".join(segment.text for segment in segments).strip()


def save_transcription(input_path: Path, output_dir: Path, text: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{input_path.stem}.txt"
    output_file.write_text(text, encoding="utf-8")
    return output_file


def transcribe_to_file(input_path: Path, output_dir: Path) -> Path:
    text = transcribe_path(input_path)
    return save_transcription(input_path, output_dir, text)
