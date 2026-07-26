from speechkit.normalize import normalize_batch_output


def test_normalizes_diarized_turns_and_preserves_raw_chunks():
    artifact = normalize_batch_output(
        asset_id="asset-1",
        filename="meeting.mp4",
        duration_seconds=10.0,
        output={
            "request_id": "req-1",
            "transcript": "Hello there. Yes, hello.",
            "language_code": "en-IN",
            "language_probability": 0.98,
            "timestamps": {
                "chunks": ["Hello there.", "Yes, hello."],
                "start_time_seconds": [0.0, 3.0],
                "end_time_seconds": [2.0, 5.0],
            },
            "diarized_transcript": {
                "entries": [
                    {"transcript": "Hello there.", "start_time_seconds": 0.0, "end_time_seconds": 2.0, "speaker_id": "0"},
                    {"transcript": "Yes, hello.", "start_time_seconds": 3.0, "end_time_seconds": 5.0, "speaker_id": "1"},
                ]
            },
        },
        job_id="job-1",
        estimated_cost_inr=0.08,
    )

    assert [segment.speaker_id for segment in artifact.segments] == ["speaker_0", "speaker_1"]
    assert artifact.segments[0].start_seconds == 0.0
    assert artifact.metadata["sarvam_timestamps"]["chunks"] == ["Hello there.", "Yes, hello."]
    assert artifact.metadata["sarvam_request_id"] == "req-1"


def test_handles_missing_optional_fields_and_empty_diarization():
    artifact = normalize_batch_output(
        asset_id="asset-1", filename="empty.wav", duration_seconds=1.0,
        output={"transcript": "", "diarized_transcript": {"entries": []}},
        job_id="job-1", estimated_cost_inr=0.01,
    )
    assert artifact.language_code is None
    assert artifact.segments == []
