#!/usr/bin/env python3
"""
Teste isolado de diarização pyannote (sem GUI).

Uso (na raiz do repositório):
  pip install -e ".[diarization]"
  set HF_TOKEN=seu_token_hf
  python scripts/test_pyannote_diarization.py caminho\\audio.mp3

Opcional: transcrever antes com faster-whisper (mais lento):
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
    parser = argparse.ArgumentParser(description="Teste pyannote community-1")
    parser.add_argument("audio", help="Arquivo de áudio ou vídeo")
    parser.add_argument(
        "--transcribe",
        action="store_true",
        help="Transcrever com faster-whisper antes de rotular falantes",
    )
    parser.add_argument("--device", default="cpu", choices=("cpu", "cuda"))
    args = parser.parse_args()

    audio_path = Path(args.audio).resolve()
    if not audio_path.is_file():
        print(f"Arquivo não encontrado: {audio_path}", file=sys.stderr)
        return 1

    from audiotranscriber.services.diarization_pyannote import (
        assign_speakers,
        install_hint,
        is_pyannote_available,
    )

    if not is_pyannote_available():
        print(install_hint(), file=sys.stderr)
        return 1

    segments = []
    if args.transcribe:
        from audiotranscriber.core.settings import TranscriptionSettings
        from audiotranscriber.services import TranscriptionService

        print("Transcrevendo com faster-whisper…", file=sys.stderr)
        service = TranscriptionService()
        settings = TranscriptionSettings.from_quality_preset("rapida")
        model = service._models.get_model(settings)
        segs, _info = model.transcribe(str(audio_path), vad_filter=True)
        segments = list(segs)
    else:
        print(
            "Modo rápido: apenas diarização pyannote (sem texto).\n"
            "Use --transcribe para alinhar falantes a trechos transcritos.",
            file=sys.stderr,
        )
        class _FakeSegment:
            def __init__(self, start: float, end: float) -> None:
                self.start = start
                self.end = end
                self.text = f"[trecho {start:.1f}s]"

        from audiotranscriber.services.diarization_pyannote import _load_pipeline

        pipeline = _load_pipeline(args.device)
        output = pipeline(str(audio_path))
        from audiotranscriber.services.diarization_pyannote import _collect_turns

        for start, end, speaker in _collect_turns(output):
            print(f"{start:7.2f}s - {end:7.2f}s  {speaker}")
        return 0

    print("Diarizando falantes (pyannote)…", file=sys.stderr)
    labeled = assign_speakers(audio_path, segments, device=args.device)
    for item in labeled:
        print(f"[{item['speaker']}] {item['text']}")
    print(f"\n{len(labeled)} trecho(s) rotulado(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
