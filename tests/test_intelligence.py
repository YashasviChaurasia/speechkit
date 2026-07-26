from speechkit.intelligence import build_speaker_profiles, enrich_segments
from speechkit.models import SpeechSegment


def test_calculates_speaker_metrics_questions_and_keywords():
    segments = enrich_segments([
        SpeechSegment("a", "asset", "speaker_0", "Speaker 0", "Can AWS deploy the payment service?", 0, 4),
        SpeechSegment("b", "asset", "speaker_0", "Speaker 0", "The AWS payment deployment is ready.", 5, 8),
        SpeechSegment("c", "asset", "speaker_1", "Speaker 1", "Yes, Acme Corp approved it.", 8, 10),
    ])
    profiles = {profile.speaker_id: profile for profile in build_speaker_profiles(segments)}

    assert profiles["speaker_0"].speaking_seconds == 7
    assert profiles["speaker_0"].speaking_percentage == 77.8
    assert profiles["speaker_0"].questions_asked == 1
    assert "aws" in profiles["speaker_0"].keywords
    assert profiles["speaker_1"].entities == ["Acme Corp"]


def test_intelligence_handles_empty_segments():
    assert build_speaker_profiles([]) == []
