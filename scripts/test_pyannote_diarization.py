#!/usr/bin/env python3
"""Teste de diarização local (sem Hugging Face).

  pip install -e ".[diarization]"
  python scripts/test_pyannote_diarization.py audio.mp3 --transcribe
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main() -> int:
    parser = argparse.ArgumentParser(description="Teste diarização local")
    parser.add_argument("audio", help="Arquivo de áudio ou vídeo")
    parser.add_argument(
        "--transcribe",
        action="store_true",
        help="Transcrever com faster-whisper antes",
    )
    args = parser.parse_args()

    audio_path = Path(args.audio).resolve()
    if not audio_path.is_file():
        print(f"Arquivo não encontrado: {audio_path}", file=sys.stderr)
        return 1

    from audiotranscriber.services.diarization_local import (
        assign_speakers,
        install_hint,
        is_local_diarization_available,
    )

    if not is_local_diarization_available():
        print(install_hint(), file=sys.stderr)
        return 1

    if not args.transcribe:
        print("Use --transcribe para alinhar falantes aos trechos do Whisper.", file=sys.stderr)
        return 1

    from audiotranscriber.core.settings import TranscriptionSettings
    from audiotranscriber.services import TranscriptionService

    service = TranscriptionService()
    settings = TranscriptionSettings.from_quality_preset("rapida")
    model = service._models.get_model(settings)
    segments, _ = model.transcribe(str(audio_path), vad_filter=True)
    segments = list(segments)

    labeled = assign_speakers(audio_path, segments)
    for item in labeled:
        print(f"[{item['speaker']}] {item['text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
