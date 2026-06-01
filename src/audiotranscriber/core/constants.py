MODEL_OPTIONS = ("tiny", "base", "small", "medium", "large-v3")
COMPUTE_OPTIONS = ("int8", "float16", "float32")
MEMORY_PROFILE_OPTIONS = ("low", "balanced", "high")
QUALITY_PRESET_OPTIONS = ("rapida", "equilibrada", "alta", "personalizado")
EXPORT_FORMAT_OPTIONS = ("txt", "srt", "vtt", "json")

MEMORY_PRESETS = {
    "low": {"cpu_threads": 2, "num_workers": 1, "chunk_length": 15, "beam_size": 1},
    "balanced": {
        "cpu_threads": 0,
        "num_workers": 1,
        "chunk_length": None,
        "beam_size": 5,
    },
    "high": {"cpu_threads": 0, "num_workers": 1, "chunk_length": 30, "beam_size": 5},
}
