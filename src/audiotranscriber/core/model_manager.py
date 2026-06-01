from __future__ import annotations

import threading

from faster_whisper import WhisperModel

from audiotranscriber.config import get_app_config
from audiotranscriber.core.memory import resolve_memory_settings
from audiotranscriber.core.settings import TranscriptionSettings


class ModelManager:
    """Cache thread-safe do modelo Whisper."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._model: WhisperModel | None = None
        self._cache_key: tuple | None = None

    @property
    def device(self) -> str:
        return get_app_config().device

    def get_model(self, settings: TranscriptionSettings) -> WhisperModel:
        memory = resolve_memory_settings(
            settings.memory_profile,
            beam_size=settings.beam_size,
        )
        cache_key = (
            settings.model_size,
            self.device,
            settings.compute_type,
            memory["cpu_threads"],
            memory["num_workers"],
        )

        with self._lock:
            if self._model is None or self._cache_key != cache_key:
                self._model = WhisperModel(
                    settings.model_size,
                    device=self.device,
                    compute_type=settings.compute_type,
                    cpu_threads=memory["cpu_threads"],
                    num_workers=memory["num_workers"],
                )
                self._cache_key = cache_key
            return self._model


_default_manager: ModelManager | None = None
_manager_lock = threading.Lock()


def get_model_manager() -> ModelManager:
    global _default_manager
    with _manager_lock:
        if _default_manager is None:
            _default_manager = ModelManager()
        return _default_manager
