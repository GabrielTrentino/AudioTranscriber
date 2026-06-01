"""
Compatibilidade com imports legados (`from legacy_transcriber import …`).

Prefira: `pip install -e .` e `from audiotranscriber…`.
Execute a partir da raiz do repositório ou use o pacote instalado.
"""

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from audiotranscriber.config import AppConfig, get_app_config
from audiotranscriber.core import (
    COMPUTE_OPTIONS,
    MEMORY_PROFILE_OPTIONS,
    MODEL_OPTIONS,
    QUALITY_PRESET_OPTIONS,
    TranscriptionCancelled,
    TranscriptionSettings,
    format_segments,
    get_model_manager,
)
from audiotranscriber.core.model_manager import ModelManager
from audiotranscriber.services import TranscriptionService
from audiotranscriber.services.transcription_service import (
    resolve_output_filename,
)

_config = get_app_config()
DEVICE = _config.device
PAUSE_GAP_SECONDS = _config.pause_gap_seconds
OUTPUT_FORMAT = _config.output_format

_default_service = TranscriptionService()


def get_model(settings: TranscriptionSettings):
    return get_model_manager().get_model(settings)


def resolve_memory_settings(profile: str, *, beam_size: int | None = None) -> dict:
    from audiotranscriber.core.memory import resolve_memory_settings as _resolve

    return _resolve(profile, beam_size=beam_size)


def transcribe_path(*args, **kwargs):
    return _default_service.transcribe_path(*args, **kwargs)


def save_transcription(*args, **kwargs):
    return _default_service.save_transcription(*args, **kwargs)


def transcribe_to_file(*args, **kwargs):
    return _default_service.transcribe_to_file(*args, **kwargs)


__all__ = [
    "AppConfig",
    "COMPUTE_OPTIONS",
    "DEVICE",
    "MEMORY_PROFILE_OPTIONS",
    "MODEL_OPTIONS",
    "OUTPUT_FORMAT",
    "PAUSE_GAP_SECONDS",
    "QUALITY_PRESET_OPTIONS",
    "TranscriptionCancelled",
    "TranscriptionSettings",
    "ModelManager",
    "TranscriptionService",
    "format_segments",
    "get_app_config",
    "get_model",
    "get_model_manager",
    "resolve_memory_settings",
    "resolve_output_filename",
    "save_transcription",
    "transcribe_path",
    "transcribe_to_file",
]
