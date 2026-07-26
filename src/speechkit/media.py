from __future__ import annotations
import json, subprocess
from dataclasses import dataclass
from pathlib import Path
from .exceptions import MediaError

@dataclass(frozen=True)
class MediaInfo: duration_seconds: float; format_name: str

def inspect_media(path: Path, ffprobe: str = "ffprobe") -> MediaInfo:
    try:
        out = subprocess.run([ffprobe,"-v","error","-show_entries","format=duration,format_name:stream=codec_type","-of","json",str(path)], capture_output=True, text=True, timeout=30, check=True)
        data=json.loads(out.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as e: raise MediaError(f"ffprobe failed: {e}") from e
    if not any(s.get("codec_type")=="audio" for s in data.get("streams", [])): raise MediaError("Upload has no audio stream.")
    return MediaInfo(float(data["format"]["duration"]), data["format"].get("format_name", "unknown"))

def extract_audio(source: Path, target: Path, ffmpeg: str = "ffmpeg") -> Path:
    try: subprocess.run([ffmpeg,"-y","-i",str(source),"-vn","-ac","1","-ar","16000","-c:a","pcm_s16le",str(target)], capture_output=True, text=True, timeout=300, check=True)
    except (OSError, subprocess.SubprocessError) as e: raise MediaError(f"FFmpeg audio extraction failed: {getattr(e, 'stderr', e)}") from e
    return target
