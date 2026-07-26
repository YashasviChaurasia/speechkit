from __future__ import annotations

import uuid

from .intelligence import build_speaker_profiles, enrich_segments
from .models import SpeechArtifact, SpeechSegment


def normalize_batch_output(*, asset_id: str, filename: str, duration_seconds: float, output: dict, job_id: str, estimated_cost_inr: float, file_failures: list[dict] | None = None) -> SpeechArtifact:
    entries = ((output.get("diarized_transcript") or {}).get("entries") or [])
    segments = []
    for index, entry in enumerate(entries):
        raw_speaker = str(entry.get("speaker_id", "unknown"))
        speaker_id = raw_speaker if raw_speaker.startswith("speaker_") else f"speaker_{raw_speaker}"
        seed = f"{asset_id}:{index}:{entry.get('start_time_seconds', 0)}"
        segments.append(SpeechSegment(
            segment_id=f"seg_{uuid.uuid5(uuid.NAMESPACE_URL, seed)}",
            asset_id=asset_id, speaker_id=speaker_id, speaker_name=f"Speaker {raw_speaker}",
            text=str(entry.get("transcript") or "").strip(),
            start_seconds=float(entry.get("start_time_seconds") or 0), end_seconds=float(entry.get("end_time_seconds") or 0),
        ))
    enrich_segments(segments)
    return SpeechArtifact(
        schema_version="speechkit.v1", asset_id=asset_id, filename=filename,
        duration_seconds=duration_seconds, provider="sarvam", model="saaras:v3",
        language_code=output.get("language_code"), speakers=build_speaker_profiles(segments), segments=segments,
        metadata={
            "sarvam_job_id": job_id, "sarvam_request_id": output.get("request_id"),
            "language_probability": output.get("language_probability"),
            "sarvam_timestamps": output.get("timestamps"), "file_failures": file_failures or [],
            "sarvam_response_metadata": {key: output[key] for key in ("audio_mime",) if key in output},
            "estimated_cost_inr": estimated_cost_inr,
        },
    )
