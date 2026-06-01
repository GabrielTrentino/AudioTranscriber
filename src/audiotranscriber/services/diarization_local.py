"""
Diarização local sem Hugging Face: MFCC + agrupamento (scikit-learn + librosa).

Sem download de modelos gated; só dependências pip.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

_MIN_SEGMENT_SEC = 0.35
# Distância de cosseno (0=idêntico, 1=ortogonal): maior = menos clusters
_CLUSTER_DISTANCE = 0.55
_SMOOTH_SIMILARITY = 0.82


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
    delta = librosa.feature.delta(mfcc)
    combined = np.concatenate([mfcc.mean(axis=1), delta.mean(axis=1)])
    norm = np.linalg.norm(combined)
    if norm < 1e-8:
        return None
    return combined / norm


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def _smooth_labels_in_order(
    cluster_ids: np.ndarray, embeddings: list[np.ndarray]
) -> np.ndarray:
    """Evita trocar de falante entre trechos consecutivos da mesma voz."""
    smoothed = cluster_ids.copy()
    for i in range(1, len(smoothed)):
        if _cosine_similarity(embeddings[i], embeddings[i - 1]) >= _SMOOTH_SIMILARITY:
            smoothed[i] = smoothed[i - 1]
    return smoothed


def _merge_similar_clusters(cluster_ids: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Une clusters com centroides muito parecidos (mesma pessoa)."""
    unique = [int(c) for c in np.unique(cluster_ids)]
    if len(unique) <= 1:
        return cluster_ids

    centroids: dict[int, np.ndarray] = {}
    for cid in unique:
        mean = matrix[cluster_ids == cid].mean(axis=0)
        norm = np.linalg.norm(mean)
        centroids[cid] = mean / norm if norm > 1e-8 else mean

    remap = {cid: cid for cid in unique}
    for i, a in enumerate(unique):
        for b in unique[i + 1 :]:
            if _cosine_similarity(centroids[a], centroids[b]) >= _SMOOTH_SIMILARITY:
                remap[b] = remap[a]

    return np.array([remap[int(c)] for c in cluster_ids])


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
        if not segment.text.strip():
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
                metric="cosine",
                linkage="average",
            )
            cluster_ids = model.fit_predict(matrix)
            emb_list = [rows[i] for i in range(len(rows))]
            cluster_ids = _smooth_labels_in_order(cluster_ids, emb_list)
            cluster_ids = _merge_similar_clusters(cluster_ids, matrix)

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
