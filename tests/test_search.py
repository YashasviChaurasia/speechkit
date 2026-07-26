from speechkit.models import SpeechArtifact, SpeechSegment, SpeakerProfile
from speechkit.storage import Storage


def artifact() -> SpeechArtifact:
    return SpeechArtifact(
        "speechkit.v1", "asset-1", "meeting.mp4", 10, "sarvam", "saaras:v3", "en-IN",
        [SpeakerProfile("speaker_0", "Alice", 2, 100, 4, 1, 2, 2, 0, ["aws"], ["AWS"], ["AWS deployment is ready."])],
        [SpeechSegment("seg-1", "asset-1", "speaker_0", "Alice", "AWS deployment is ready.", 4.2, 6.0, ["aws", "deployment"], ["AWS"], ["aws deployment"])],
        {},
    )


def test_fts_finds_segment_and_refreshes_speaker_name(tmp_path):
    store = Storage(tmp_path / "speechlens.sqlite")
    store.save_artifact(artifact())
    result = store.search("asset-1", '"AWS deployment"')
    assert result[0]["segment_id"] == "seg-1"
    assert result[0]["start_seconds"] == 4.2

    store.rename_speaker("asset-1", "speaker_0", "Alicia")
    assert store.search("asset-1", "Alicia")[0]["speaker_name"] == "Alicia"
