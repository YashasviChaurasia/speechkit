from speechkit.normalize import normalize_batch_output


def test_speechkit_v1_artifact_has_consistent_segment_and_speaker_references():
    artifact = normalize_batch_output(
        asset_id="asset", filename="recording.wav", duration_seconds=10,
        job_id="job", estimated_cost_inr=0.125,
        output={"language_code": "en-IN", "diarized_transcript": {"entries": [
            {"transcript": "First.", "speaker_id": "0", "start_time_seconds": 1.0, "end_time_seconds": 2.0},
            {"transcript": "Second.", "speaker_id": "1", "start_time_seconds": 3.0, "end_time_seconds": 4.0},
        ]}},
    )
    exported = artifact.to_dict()
    speaker_ids = {speaker["speaker_id"] for speaker in exported["speakers"]}
    assert exported["schema_version"] == "speechkit.v1"
    assert exported["provider"] == "sarvam"
    assert exported["model"] == "saaras:v3"
    assert all(segment["speaker_id"] in speaker_ids for segment in exported["segments"])
    assert all(segment["start_seconds"] <= segment["end_seconds"] for segment in exported["segments"])
    assert exported["metadata"]["estimated_cost_inr"] == 0.125
