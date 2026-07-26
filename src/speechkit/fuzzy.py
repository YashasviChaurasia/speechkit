from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz, process


@dataclass(frozen=True)
class SearchVocabularyTerm:
    normalised_term: str
    display_term: str
    field: str
    segment_ids: list[str]


@dataclass(frozen=True)
class FuzzyCandidate:
    term: SearchVocabularyTerm
    similarity: float


def normalise_term(value: str) -> str:
    """Normalise search tokens without damaging punctuation inside entities."""
    return re.sub(r"\s+", " ", value.casefold().strip()).strip(" \t\r\n\"'“”‘’.,;:!?()[]{}")


def fuzzy_threshold(query: str) -> float | None:
    length = len(normalise_term(query))
    if length <= 3:
        return None
    return 0.85 if length <= 5 else 0.78


def fuzzy_candidates(query: str, vocabulary: list[SearchVocabularyTerm], limit: int = 5) -> list[FuzzyCandidate]:
    normalised_query = normalise_term(query)
    threshold = fuzzy_threshold(normalised_query)
    if not normalised_query or threshold is None or not vocabulary:
        return []
    matches = process.extract(
        normalised_query,
        [term.normalised_term for term in vocabulary],
        scorer=fuzz.WRatio,
        score_cutoff=threshold * 100,
        limit=limit,
    )
    return [FuzzyCandidate(vocabulary[index], round(score / 100, 4)) for _, score, index in matches]
