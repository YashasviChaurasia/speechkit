from speechkit.models import SpeechArtifact, SpeechSegment, SpeakerProfile
from speechkit.storage import Storage


def populated_store(tmp_path):
    store = Storage(tmp_path / "speechlens.sqlite")
    artifact = SpeechArtifact(
        "speechkit.v1", "asset", "demo.mp4", 20, "sarvam", "saaras:v3", "en-IN",
        [
            SpeakerProfile("speaker_0", "Alicia", 10, 50, 5, 1, 10, 10, 0, ["terraform"], ["Acme Cloud"], ["Terraform deploys."]),
            SpeakerProfile("speaker_1", "Bob", 10, 50, 5, 1, 10, 10, 1, ["customer"], ["AWS"], ["Customer managed keys."]),
        ],
        [
            SpeechSegment("one", "asset", "speaker_0", "Alicia", "Terraform deploys customer managed keys.", 1, 4, ["terraform"], ["Acme Cloud"], ["infrastructure"]),
            SpeechSegment("two", "asset", "speaker_1", "Bob", "The deployment is ready.", 5, 8, ["customer"], ["AWS"], ["deployment"]),
        ], {},
    )
    store.create_asset("asset", "demo.mp4")
    store.save_artifact(artifact)
    return store


def test_smart_token_phrase_prefix_keyword_entity_and_speaker_search(tmp_path):
    store = populated_store(tmp_path)
    assert store.search("asset", "terraform", "smart")[0]["segment_id"] == "one"
    assert store.search("asset", "customer managed", "phrase")[0]["segment_id"] == "one"
    assert {row["segment_id"] for row in store.search("asset", "deploy*", "prefix")} == {"one", "two"}
    assert store.search("asset", "AWS", "smart")[0]["segment_id"] == "two"
    assert store.search("asset", "Acme", "smart")[0]["segment_id"] == "one"
    assert store.search("asset", "Alicia", "smart")[0]["speaker_name"] == "Alicia"


def test_substring_search_and_fallback_match_middle_of_token(tmp_path):
    store = populated_store(tmp_path)
    assert store.search("asset", "ploym", "substring")[0]["segment_id"] == "two"
    store.trigram_available = False
    assert store.search("asset", "ploym", "substring")[0]["segment_id"] == "two"


def test_search_returns_matched_fields_scores_and_timestamps(tmp_path):
    store = populated_store(tmp_path)
    result = store.search("asset", "terraform", "smart")[0]
    assert result["start_seconds"] == 1
    assert "text" in result["matched_fields"]
    assert isinstance(result["score"], float)
