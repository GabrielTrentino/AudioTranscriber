from dataclasses import dataclass

from audiotranscriber.config import get_app_config
from audiotranscriber.core.device import normalize_device


@dataclass
class TranscriptionSettings:
    model_size: str = "base"
    compute_type: str = "int8"
    memory_profile: str = "balanced"
    language: str = "pt"
    device: str = "cpu"
    beam_size: int | None = None
    quality_preset: str = "equilibrada"

    @classmethod
    def from_env(cls) -> "TranscriptionSettings":
        cfg = get_app_config()
        preset = cfg.default_quality_preset.strip().lower()
        if preset in ("rapida", "equilibrada", "alta"):
            return cls.from_quality_preset(preset)

        return cls(
            model_size=cfg.default_model,
            compute_type=cfg.default_compute_type,
            memory_profile=cfg.default_memory_profile,
            language=cfg.default_language,
            device=normalize_device(cfg.device),
            beam_size=cfg.beam_size,
            quality_preset="personalizado",
        )

    @classmethod
    def from_quality_preset(cls, preset: str) -> "TranscriptionSettings":
        cfg = get_app_config()
        device = normalize_device(cfg.device)
        presets = {
            "rapida": cls(
                model_size="base",
                memory_profile="low",
                beam_size=1,
                compute_type="int8",
                device=device,
                quality_preset="rapida",
            ),
            "equilibrada": cls(
                model_size="base",
                memory_profile="balanced",
                beam_size=5,
                compute_type="int8",
                device=device,
                quality_preset="equilibrada",
            ),
            "alta": cls(
                model_size="small",
                memory_profile="high",
                beam_size=5,
                compute_type="int8",
                device=device,
                quality_preset="alta",
            ),
        }
        return presets.get(preset, presets["equilibrada"])
