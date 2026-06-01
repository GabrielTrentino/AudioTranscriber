"""
Diarização local sem Hugging Face: MFCC + agrupamento (scikit-learn + librosa).

Sem download de modelos gated; só dependências pip.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

_MIN_SEGMENT_SEC = 0.35
_CLUSTER_DISTANCE = 9.0


def is_local_diarization_available() -> bool:
    try:
        import librosa  # noqa: F401
        import sklearn  # noqa: F401

        return True
    except ImportError:
        return False


def install_hint() -> str:
    return 'Instale: pip install "audiotranscriber[diarization]"'


def _load_mono_16k(audio_path: Path) -> tuple[np.ndarray, int]:
    import librosa

    samples, sr = librosa.load(str(audio_path), sr=16000, mono=True)
    return samples, sr


def _segment_embedding(
    samples: np.ndarray, sr: int, start: float, end: float
) -> np.ndarray | None:
    import librosa

    i0 = max(0, int(start * sr))
    i1 = min(len(samples), int(end * sr))
    if i1 - i0 < int(_MIN_SEGMENT_SEC * sr):
        return None
    clip = samples[i0:i1]
    mfcc = librosa.feature.mfcc(y=clip, sr=sr, n_mfcc=20)
    return mfcc.mean(axis=1)


def assign_speakers(
    audio_path: Path,
    segments: list[Any],
    *,
    device: str = "cpu",
    language: str | None = None,
) -> list[dict[str, Any]]:
    del device, language
    if not is_local_diarization_available():
        raise ImportError(install_hint())

    from sklearn.cluster import AgglomerativeClustering

    samples, sr = _load_mono_16k(audio_path)
    rows: list[np.ndarray] = []
    indices: list[int] = []

    for index, segment in enumerate(segments):
        text = segment.text.strip()
        if not text:
            continue
        emb = _segment_embedding(samples, sr, float(segment.start), float(segment.end))
        if emb is None:
            continue
        rows.append(emb)
        indices.append(index)

    labels = ["SPEAKER_00"] * len(segments)
    if rows:
        matrix = np.vstack(rows)
        if len(rows) == 1:
            cluster_ids = np.array([0])
        else:
            model = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=_CLUSTER_DISTANCE,
                metric="euclidean",
                linkage="average",
            )
            cluster_ids = model.fit_predict(matrix)
        for seg_index, cluster_id in zip(indices, cluster_ids):
            labels[seg_index] = f"SPEAKER_{int(cluster_id):02d}"

    result: list[dict[str, Any]] = []
    for segment, speaker in zip(segments, labels):
        text = segment.text.strip()
        if not text:
            continue
        result.append(
            {
                "start": float(segment.start),
                "end": float(segment.end),
                "text": text,
                "speaker": speaker,
            }
        )
    return result
