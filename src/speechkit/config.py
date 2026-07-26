from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
@dataclass(frozen=True)
class Settings:
    data_dir: Path
    fixture_mode: bool = False
    poll_interval: int = 5
    batch_timeout: int = 1800
    max_upload_bytes: int = 500 * 1024 * 1024
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"

    @classmethod
    def from_env(cls) -> "Settings":
        fixture_mode = os.getenv("SPEECHKIT_FIXTURE_MODE") == "1"
        data_dir = Path(os.getenv("SPEECHKIT_DATA_DIR", "./data")).resolve()
        data_dir.mkdir(parents=True, exist_ok=True)
        return cls(data_dir, fixture_mode)
