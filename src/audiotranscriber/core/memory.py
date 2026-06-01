from audiotranscriber.config import get_app_config
from audiotranscriber.core.constants import MEMORY_PRESETS


def resolve_memory_settings(
    profile: str,
    *,
    beam_size: int | None = None,
) -> dict:
    profile = profile if profile in MEMORY_PRESETS else "balanced"
    settings = dict(MEMORY_PRESETS[profile])
    cfg = get_app_config()

    if cfg.cpu_threads is not None:
        settings["cpu_threads"] = cfg.cpu_threads
    if cfg.num_workers is not None:
        settings["num_workers"] = cfg.num_workers
    if cfg.chunk_length is not None:
        settings["chunk_length"] = cfg.chunk_length

    if beam_size is not None:
        settings["beam_size"] = beam_size
    elif cfg.beam_size is not None:
        settings["beam_size"] = cfg.beam_size

    return settings
