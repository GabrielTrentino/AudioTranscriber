"""Interface de linha de comando: python -m audiotranscriber."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from audiotranscriber.core.settings import TranscriptionSettings
from audiotranscriber.services import TranscriptionService


def _build_settings(args: argparse.Namespace) -> TranscriptionSettings:
    if args.quality:
        settings = TranscriptionSettings.from_quality_preset(args.quality)
    else:
        settings = TranscriptionSettings.from_env()
    if args.model:
        settings.model_size = args.model
    if args.language:
        settings.language = args.language
    if args.memory_profile:
        settings.memory_profile = args.memory_profile
    if args.compute_type:
        settings.compute_type = args.compute_type
    if args.beam_size is not None:
        settings.beam_size = args.beam_size
    return settings


def _progress(ratio: float, message: str | None) -> None:
    if message:
        print(message, file=sys.stderr, flush=True)
    elif ratio >= 0:
        print(f"{int(ratio * 100)}%", file=sys.stderr, flush=True)


def cmd_transcribe(args: argparse.Namespace) -> int:
    input_path = Path(args.input).resolve()
    if not input_path.is_file():
        print(f"Arquivo não encontrado: {input_path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir).resolve() if args.output_dir else input_path.parent
    settings = _build_settings(args)
    service = TranscriptionService()

    try:
        out = service.transcribe_to_file(
            input_path,
            output_dir,
            args.output_name,
            settings=settings,
            include_timestamps=args.timestamps,
            on_progress=_progress if not args.quiet else None,
        )
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    print(out)
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    paths = [Path(p).resolve() for p in args.inputs]
    missing = [p for p in paths if not p.is_file()]
    if missing:
        for path in missing:
            print(f"Arquivo não encontrado: {path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    use_input_folder = output_dir is None
    settings = _build_settings(args)
    service = TranscriptionService()

    saved = 0
    failed = 0
    for index, input_path in enumerate(paths):
        target = input_path.parent if use_input_folder else output_dir
        assert target is not None

        def file_progress(ratio: float, message: str | None, *, idx=index) -> None:
            if args.quiet:
                return
            label = paths[idx].name
            pct = int(ratio * 100) if ratio >= 0 else 0
            print(f"[{idx + 1}/{len(paths)}] {label}: {pct}%", file=sys.stderr, flush=True)

        try:
            out = service.transcribe_to_file(
                input_path,
                target,
                settings=settings,
                include_timestamps=args.timestamps,
                on_progress=file_progress,
            )
            print(out)
            saved += 1
        except Exception as exc:
            print(f"Erro em {input_path.name}: {exc}", file=sys.stderr)
            failed += 1

    if failed:
        return 1 if saved == 0 else 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audiotranscriber",
        description="Transcrição local de áudio e vídeo com faster-whisper.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--quality",
        choices=("rapida", "equilibrada", "alta"),
        help="Preset de qualidade (ignora env se definido)",
    )
    common.add_argument("--model", help="Tamanho do modelo Whisper")
    common.add_argument("--language", default=None, help="Idioma (pt, en, auto, …)")
    common.add_argument("--memory-profile", dest="memory_profile")
    common.add_argument("--compute-type", dest="compute_type")
    common.add_argument("--beam-size", dest="beam_size", type=int)
    common.add_argument(
        "--timestamps",
        action="store_true",
        help="Incluir marcações de tempo no .txt",
    )
    common.add_argument("-q", "--quiet", action="store_true", help="Sem progresso no stderr")

    p_one = sub.add_parser("transcribe", parents=[common], help="Transcrever um arquivo")
    p_one.add_argument("input", help="Arquivo de áudio ou vídeo")
    p_one.add_argument("-o", "--output-dir", help="Pasta de saída (padrão: pasta do arquivo)")
    p_one.add_argument("--output-name", help="Nome do arquivo .txt de saída")
    p_one.set_defaults(func=cmd_transcribe)

    p_batch = sub.add_parser("batch", parents=[common], help="Transcrever vários arquivos")
    p_batch.add_argument("inputs", nargs="+", help="Arquivos de entrada")
    p_batch.add_argument(
        "-o",
        "--output-dir",
        help="Pasta única de saída (padrão: pasta de cada arquivo)",
    )
    p_batch.set_defaults(func=cmd_batch)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
