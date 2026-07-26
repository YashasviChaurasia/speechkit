from speechkit.models import SpeechArtifact, SpeechSegment, SpeakerProfile
from speechkit.storage import Storage


def store_with_vocabulary(tmp_path):
    store = Storage(tmp_path / "speechlens.sqlite")
    artifact = SpeechArtifact(
        "speechkit.v1", "asset", "demo.wav", 20, "sarvam", "saaras:v3", "en-IN",
        [SpeakerProfile("one", "Alice Johnson", 10, 50, 4, 2, 5, 6, 1, [], [], []), SpeakerProfile("two", "Bob", 10, 50, 4, 2, 5, 6, 0, [], [], [])],
        [
            SpeechSegment("one", "asset", "one", "Alice Johnson", "The spider began mutating DNA.", 1, 3, ["spider", "mutating", "Experiment"], ["Experiment"], ["responsibility"]),
            SpeechSegment("two", "asset", "two", "Bob", "Spider tests are complete.", 4, 6, ["spider", "mutatingly"], ["Nebula"], []),
        ],
        {},
    )
    store.create_asset("asset", "demo.wav")
    store.save_artifact(artifact)
    return store


def test_closest_returns_deduplicated_structured_matches(tmp_path):
    store = store_with_vocabulary(tmp_path)
    result = store.search("asset", "spidr", "closest")
    assert {row["segment_id"] for row in result} == {"one", "two"}
    assert all(row["match_type"] == "fuzzy_keyword" for row in result)
    assert all(0 < row["similarity"] < 1 for row in result)


def test_fuzzy_fields_smart_fallback_and_exact_precedence(tmp_path):
    store = store_with_vocabulary(tmp_path)
    assert store.search("asset", "mutatin", "smart")[0]["match_type"] == "fuzzy_keyword"
    assert store.search("asset", "experimnt", "closest")[0]["matched_fields"] == ["keywords", "entities"]
    assert store.search("asset", "nebla", "closest")[0]["match_type"] == "fuzzy_entity"
    assert store.search("asset", "responsibilty", "closest")[0]["match_type"] == "fuzzy_topic"
    exact = store.search("asset", "spider", "smart")
    assert len(exact) == 2
    assert all(row["is_exact"] for row in exact)
    ranked = store.search("asset", "mutating", "smart")
    assert ranked[0]["is_exact"] and not ranked[1]["is_exact"]


def test_renamed_speaker_rebuilds_close_name_vocabulary(tmp_path):
    store = store_with_vocabulary(tmp_path)
    store.rename_speaker("asset", "one", "Caroline Vega")
    result = store.search("asset", "carolin", "closest")
    assert result[0]["match_type"] == "fuzzy_speaker"
    assert result[0]["speaker_name"] == "Caroline Vega"
    assert store.search("asset", "alic", "closest") == []


def test_empty_vocabulary_and_short_query_return_no_close_matches(tmp_path):
    store = Storage(tmp_path / "speechlens.sqlite")
    assert store.search("missing", "spidr", "closest") == []
    store = store_with_vocabulary(tmp_path)
    assert store.search("asset", "spi", "closest") == []
