from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from .exceptions import ConfigurationError

@dataclass(frozen=True)
class Settings:
    api_key: str
    data_dir: Path
    poll_interval: int = 5
    batch_timeout: int = 1800
    max_upload_bytes: int = 500 * 1024 * 1024
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"

    @classmethod
    def from_env(cls) -> "Settings":
        key = os.getenv("SARVAM_API_KEY")
        if not key: raise ConfigurationError("SARVAM_API_KEY is required; SpeechLens never falls back to another provider.")
        data_dir = Path(os.getenv("SPEECHKIT_DATA_DIR", "./data")).resolve()
        data_dir.mkdir(parents=True, exist_ok=True)
        return cls(key, data_dir)
