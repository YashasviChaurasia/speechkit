from __future__ import annotations

import re
from collections import Counter, defaultdict

from .models import SpeechSegment, SpeakerProfile

STOP_WORDS = frozenset("a an and are as at be by for from has have he in is it its of on or that the this to was we with you your i me my our yes no can will".split())
TOKEN = re.compile(r"[\w][\w'-]{1,}", re.UNICODE)
CAPITALIZED = re.compile(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+|[A-Z]{2,}(?:\s+[A-Z]{2,})*)\b")


def keywords(text: str, limit: int = 6) -> list[str]:
    words = [word.lower() for word in TOKEN.findall(text) if word.lower() not in STOP_WORDS]
    counts = Counter(word for word in words if len(word) > 2)
    bigrams = Counter(" ".join(pair) for pair in zip(words, words[1:]) if all(len(word) > 2 for word in pair))
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [word for word, _ in ranked[:limit]] + [phrase for phrase, count in bigrams.most_common(2) if count > 1][:2]


def entities(text: str) -> list[str]:
    found = CAPITALIZED.findall(text)
    return list(dict.fromkeys(found))[:6]


def enrich_segments(segments: list[SpeechSegment]) -> list[SpeechSegment]:
    for segment in segments:
        segment.keywords = keywords(segment.text)
        segment.entities = entities(segment.text)
        segment.topics = segment.keywords[:3]
    return segments


def build_speaker_profiles(segments: list[SpeechSegment]) -> list[SpeakerProfile]:
    by_speaker: dict[str, list[SpeechSegment]] = defaultdict(list)
    for segment in segments:
        by_speaker[segment.speaker_id].append(segment)
    total = sum(max(0.0, segment.end_seconds - segment.start_seconds) for segment in segments)
    profiles = []
    for speaker_id, turns in by_speaker.items():
        duration = sum(max(0.0, turn.end_seconds - turn.start_seconds) for turn in turns)
        words = sum(len(TOKEN.findall(turn.text)) for turn in turns)
        all_keywords = Counter(keyword for turn in turns for keyword in turn.keywords)
        all_entities = list(dict.fromkeys(entity for turn in turns for entity in turn.entities))[:6]
        ranked_quotes = sorted(turns, key=lambda turn: (len(set(TOKEN.findall(turn.text.lower()))) + len(turn.entities) * 2, len(turn.text)), reverse=True)
        profiles.append(SpeakerProfile(
            speaker_id=speaker_id,
            display_name=turns[0].speaker_name,
            speaking_seconds=round(duration, 3),
            speaking_percentage=round((duration / total * 100) if total else 0, 1),
            word_count=words,
            turn_count=len(turns),
            average_turn_seconds=round(duration / len(turns), 3),
            longest_turn_seconds=round(max((turn.end_seconds - turn.start_seconds for turn in turns), default=0), 3),
            questions_asked=sum(turn.text.count("?") for turn in turns),
            keywords=[word for word, _ in all_keywords.most_common(8)],
            entities=all_entities,
            representative_quotes=[turn.text for turn in ranked_quotes[:2]],
        ))
    return profiles
