import os
import sys
from pathlib import Path


def setup_ffmpeg_path() -> None:
    """Permite colocar ffmpeg.exe na pasta do .exe ou do projeto."""
    if getattr(sys, "frozen", False):
        app_dir = Path(sys.executable).resolve().parent
    else:
        app_dir = Path(__file__).resolve().parents[3]

    if (app_dir / "ffmpeg.exe").is_file():
        os.environ["PATH"] = str(app_dir) + os.pathsep + os.environ.get("PATH", "")


setup_ffmpeg_path()
