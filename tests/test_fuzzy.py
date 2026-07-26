from speechkit.fuzzy import SearchVocabularyTerm, fuzzy_candidates, fuzzy_threshold, normalise_term


VOCABULARY = [
    SearchVocabularyTerm("spider", "Spider", "keywords", ["one"]),
    SearchVocabularyTerm("mutating", "mutating", "keywords", ["two"]),
    SearchVocabularyTerm("responsibility", "responsibility", "topics", ["three"]),
    SearchVocabularyTerm("experiment", "Experiment", "entities", ["four"]),
    SearchVocabularyTerm("alice johnson", "Alice Johnson", "speaker_name", ["five"]),
]


def test_normalises_unicode_whitespace_and_surrounding_punctuation():
    assert normalise_term("  “Node.js”  ") == "node.js"
    assert normalise_term("  ALICE   JOHNSON ") == "alice johnson"


def test_length_aware_thresholds():
    assert fuzzy_threshold("abc") is None
    assert fuzzy_threshold("spid") == 0.85
    assert fuzzy_threshold("spider") == 0.78


def test_close_tokens_return_decimal_similarity_and_never_weak_matches():
    for query, term in (("spidr", "Spider"), ("mutatin", "mutating"), ("responsibilty", "responsibility")):
        candidate = fuzzy_candidates(query, VOCABULARY)[0]
        assert candidate.term.display_term == term
        assert 0 <= candidate.similarity <= 1
    assert fuzzy_candidates("xyzq", VOCABULARY) == []


def test_short_queries_do_not_fuzzy_match():
    assert fuzzy_candidates("spi", VOCABULARY) == []
