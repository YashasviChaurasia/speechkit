from __future__ import annotations
import json, math, subprocess
from dataclasses import dataclass
from pathlib import Path
from .exceptions import MediaError, UnsupportedMediaError

SUPPORTED_UPLOAD_SUFFIXES = frozenset({".aac", ".avi", ".flac", ".m4a", ".mkv", ".mov", ".mp3", ".mp4", ".mpeg", ".mpg", ".ogg", ".opus", ".wav", ".webm"})

@dataclass(frozen=True)
class MediaInfo: duration_seconds: float; format_name: str


def validate_upload_filename(filename: str) -> str:
    safe_name = Path(filename).name
    if not safe_name or safe_name == "." or Path(safe_name).suffix.lower() not in SUPPORTED_UPLOAD_SUFFIXES:
        raise UnsupportedMediaError("Unsupported upload type. Choose a common audio or video file such as WAV, MP3, M4A, MP4, MOV, MKV, or WebM.")
    return safe_name

def inspect_media(path: Path, ffprobe: str = "ffprobe") -> MediaInfo:
    if not path.is_file() or path.stat().st_size == 0:
        raise MediaError("Upload is empty or unreadable.")
    try:
        out = subprocess.run([ffprobe,"-v","error","-show_entries","format=duration,format_name:stream=codec_type","-of","json",str(path)], capture_output=True, text=True, timeout=30, check=True)
        data=json.loads(out.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as e: raise MediaError(f"ffprobe failed: {e}") from e
    streams = data.get("streams")
    format_data = data.get("format")
    if not isinstance(streams, list) or not isinstance(format_data, dict):
        raise MediaError("Upload is not a readable audio or video file.")
    if not any(isinstance(stream, dict) and stream.get("codec_type")=="audio" for stream in streams): raise MediaError("Upload has no audio stream.")
    try:
        duration = float(format_data["duration"])
    except (KeyError, TypeError, ValueError) as e:
        raise MediaError("Upload has no usable duration.") from e
    if not math.isfinite(duration) or duration <= 0:
        raise MediaError("Upload has no usable duration.")
    return MediaInfo(duration, format_data.get("format_name", "unknown"))

def extract_audio(source: Path, target: Path, ffmpeg: str = "ffmpeg") -> Path:
    try: subprocess.run([ffmpeg,"-y","-i",str(source),"-vn","-ac","1","-ar","16000","-c:a","pcm_s16le",str(target)], capture_output=True, text=True, timeout=300, check=True)
    except (OSError, subprocess.SubprocessError) as e: raise MediaError("FFmpeg could not extract a usable audio track.") from e
    if not target.is_file() or target.stat().st_size <= 44:
        raise MediaError("FFmpeg produced an empty audio track.")
    return target
