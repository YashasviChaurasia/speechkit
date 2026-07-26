from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class SpeechSegment:
    segment_id: str
    asset_id: str
    speaker_id: str
    speaker_name: str
    text: str
    start_seconds: float
    end_seconds: float
    keywords: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)


@dataclass
class SpeakerProfile:
    speaker_id: str
    display_name: str
    speaking_seconds: float
    speaking_percentage: float
    word_count: int
    turn_count: int
    average_turn_seconds: float
    longest_turn_seconds: float
    questions_asked: int
    keywords: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    representative_quotes: list[str] = field(default_factory=list)


@dataclass
class SpeechArtifact:
    schema_version: str
    asset_id: str
    filename: str
    duration_seconds: float
    provider: str
    model: str
    language_code: str | None
    speakers: list[SpeakerProfile]
    segments: list[SpeechSegment]
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)
