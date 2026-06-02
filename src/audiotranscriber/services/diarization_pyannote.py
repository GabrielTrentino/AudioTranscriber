"""
Diarização com pyannote (Hugging Face) — speaker-diarization-community-1.

Requisitos:
  pip install "audiotranscriber[diarization]"
  Aceitar termos em https://huggingface.co/pyannote/speaker-diarization-community-1
  Variável HF_TOKEN (ou HUGGINGFACE_TOKEN) com token de leitura.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from audiotranscriber.services.diarization_common import (
    assign_speakers_to_segments,
    collect_pyannote_turns,
    diarization_model_id,
    diarization_speaker_count_options,
    hf_token,
    normalize_speaker_labels,
)

_PIPELINE_ACCEPT_URL = (
    "https://huggingface.co/pyannote/speaker-diarization-community-1"
)


class PyannoteNotAvailableError(ImportError):
    """pyannote.audio não instalado ou token HF ausente."""


def is_pyannote_installed() -> bool:
    try:
        import pyannote.audio  # noqa: F401

        return True
    except ImportError:
        return False


def is_pyannote_ready() -> bool:
    return is_pyannote_installed() and hf_token() is not None


def is_pyannote_available() -> bool:
    """Compatibilidade com código que só checava import."""
    return is_pyannote_ready()


def install_hint() -> str:
    return (
        "Instale: pip install \"audiotranscriber[diarization]\"\n"
        f"Aceite os termos do modelo: {_PIPELINE_ACCEPT_URL}\n"
        "Defina HF_TOKEN com um token de leitura do Hugging Face."
    )


@lru_cache(maxsize=2)
def _load_pipeline(device: str):
    import torch
    from pyannote.audio import Pipeline

    token = hf_token()
    if not token:
        raise PyannoteNotAvailableError(
            "Token Hugging Face ausente. Defina HF_TOKEN no ambiente.\n" + install_hint()
        )

    model_id = diarization_model_id()
    pipeline = Pipeline.from_pretrained(model_id, token=token)
    torch_device = torch.device("cuda" if device == "cuda" else "cpu")
    pipeline.to(torch_device)
    return pipeline


def _load_audio_input(audio_path: Path, sample_rate: int = 16000) -> dict:
    """Decodifica via FFmpeg (evita torchcodec quebrado no Windows)."""
    import subprocess

    import numpy as np
    import torch

    from audiotranscriber.core.startup_checks import find_ffmpeg

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError(
            "FFmpeg não encontrado. Instale FFmpeg ou coloque ffmpeg.exe na pasta do app."
        )

    cmd = [
        str(ffmpeg),
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(audio_path),
        "-f",
        "f32le",
        "-acodec",
        "pcm_f32le",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"FFmpeg falhou ao decodificar áudio: {err}")

    samples = np.frombuffer(proc.stdout, dtype=np.float32)
    if samples.size == 0:
        raise RuntimeError("Áudio vazio ou sem faixa de som detectável.")

    waveform = torch.from_numpy(samples.copy()).unsqueeze(0)
    return {"waveform": waveform, "sample_rate": sample_rate}


def _run_diarization(pipeline, audio_path: Path):
    opts = diarization_speaker_count_options()
    kwargs = {
        key: value
        for key, value in opts.items()
        if value is not None
    }
    audio_in = _load_audio_input(audio_path)
    return pipeline(audio_in, **kwargs)


def assign_speakers(
    audio_path: Path,
    segments: list[Any],
    *,
    device: str = "cpu",
    language: str | None = None,
) -> list[dict[str, Any]]:
    """Atribui rótulo de falante a cada segmento transcrito (pyannote + HF)."""
    del language
    if not is_pyannote_installed():
        raise PyannoteNotAvailableError(install_hint())
    if not hf_token():
        raise PyannoteNotAvailableError(
            "Token Hugging Face ausente. Defina HF_TOKEN.\n" + install_hint()
        )

    pipeline = _load_pipeline(device)
    diarization = _run_diarization(pipeline, audio_path)
    turns = collect_pyannote_turns(diarization)
    labeled = assign_speakers_to_segments(turns, segments)
    return normalize_speaker_labels(labeled)
