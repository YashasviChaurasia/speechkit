from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .fuzzy import SearchVocabularyTerm, fuzzy_candidates, normalise_term
from .models import SpeechArtifact


class Storage:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._init()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init(self) -> None:
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS assets (asset_id TEXT PRIMARY KEY, filename TEXT NOT NULL, duration_seconds REAL NOT NULL, status TEXT NOT NULL, error TEXT, metadata TEXT NOT NULL DEFAULT '{}');
                CREATE TABLE IF NOT EXISTS speakers (asset_id TEXT NOT NULL, speaker_id TEXT NOT NULL, display_name TEXT NOT NULL, profile TEXT NOT NULL, PRIMARY KEY(asset_id, speaker_id));
                CREATE TABLE IF NOT EXISTS segments (segment_id TEXT PRIMARY KEY, asset_id TEXT NOT NULL, speaker_id TEXT NOT NULL, text TEXT NOT NULL, start_seconds REAL NOT NULL, end_seconds REAL NOT NULL, keywords TEXT NOT NULL, entities TEXT NOT NULL, topics TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (asset_id TEXT PRIMARY KEY, provider_job_id TEXT, state TEXT NOT NULL, details TEXT NOT NULL DEFAULT '{}');
                CREATE VIRTUAL TABLE IF NOT EXISTS segment_fts USING fts5(segment_id UNINDEXED, asset_id UNINDEXED, text, keywords, entities, topics, speaker_name);
            """)
            try:
                db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS segment_trigram USING fts5(segment_id UNINDEXED, asset_id UNINDEXED, text, keywords, entities, speaker_name, tokenize='trigram')")
                self.trigram_available = True
            except sqlite3.OperationalError:
                self.trigram_available = False

    def create_asset(self, asset_id: str, filename: str) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO assets(asset_id, filename, duration_seconds, status) VALUES (?, ?, 0, 'uploaded')", (asset_id, filename))

    def set_status(self, asset_id: str, status: str, error: str | None = None) -> None:
        with self._connect() as db:
            db.execute("UPDATE assets SET status=?, error=? WHERE asset_id=?", (status, error, asset_id))

    def save_artifact(self, artifact: SpeechArtifact) -> None:
        with self._connect() as db:
            db.execute("UPDATE assets SET filename=?, duration_seconds=?, status='complete', error=NULL, metadata=? WHERE asset_id=?", (artifact.filename, artifact.duration_seconds, json.dumps(artifact.metadata), artifact.asset_id))
            db.execute("DELETE FROM speakers WHERE asset_id=?", (artifact.asset_id,))
            db.execute("DELETE FROM segments WHERE asset_id=?", (artifact.asset_id,))
            db.execute("DELETE FROM segment_fts WHERE asset_id=?", (artifact.asset_id,))
            if self.trigram_available: db.execute("DELETE FROM segment_trigram WHERE asset_id=?", (artifact.asset_id,))
            for speaker in artifact.speakers:
                db.execute("INSERT INTO speakers VALUES (?, ?, ?, ?)", (artifact.asset_id, speaker.speaker_id, speaker.display_name, json.dumps(speaker.__dict__)))
            for segment in artifact.segments:
                db.execute("INSERT INTO segments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (segment.segment_id, segment.asset_id, segment.speaker_id, segment.text, segment.start_seconds, segment.end_seconds, json.dumps(segment.keywords), json.dumps(segment.entities), json.dumps(segment.topics)))
                db.execute("INSERT INTO segment_fts VALUES (?, ?, ?, ?, ?, ?, ?)", (segment.segment_id, segment.asset_id, segment.text, " ".join(segment.keywords), " ".join(segment.entities), " ".join(segment.topics), segment.speaker_name))
                if self.trigram_available: db.execute("INSERT INTO segment_trigram VALUES (?, ?, ?, ?, ?, ?)", (segment.segment_id, segment.asset_id, segment.text, " ".join(segment.keywords), " ".join(segment.entities), segment.speaker_name))

    def get_asset(self, asset_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM assets WHERE asset_id=?", (asset_id,)).fetchone()
            return dict(row) if row else None

    def get_artifact(self, asset_id: str) -> dict | None:
        asset = self.get_asset(asset_id)
        if not asset or asset["status"] != "complete": return None
        with self._connect() as db:
            speakers = [json.loads(row["profile"]) for row in db.execute("SELECT profile FROM speakers WHERE asset_id=?", (asset_id,))]
            segments = [dict(row) for row in db.execute("SELECT * FROM segments WHERE asset_id=? ORDER BY start_seconds", (asset_id,))]
        for segment in segments:
            segment["speaker_name"] = next((speaker["display_name"] for speaker in speakers if speaker["speaker_id"] == segment["speaker_id"]), segment["speaker_id"])
            for key in ("keywords", "entities", "topics"): segment[key] = json.loads(segment[key])
        return {"schema_version": "speechkit.v1", "asset_id": asset_id, "filename": asset["filename"], "duration_seconds": asset["duration_seconds"], "provider": "sarvam", "model": "saaras:v3", "language_code": json.loads(asset["metadata"]).get("language_code"), "speakers": speakers, "segments": segments, "metadata": json.loads(asset["metadata"])}

    def rename_speaker(self, asset_id: str, speaker_id: str, display_name: str) -> None:
        with self._connect() as db:
            row = db.execute("SELECT profile FROM speakers WHERE asset_id=? AND speaker_id=?", (asset_id, speaker_id)).fetchone()
            if not row: raise KeyError(speaker_id)
            profile = json.loads(row["profile"]); profile["display_name"] = display_name
            db.execute("UPDATE speakers SET display_name=?, profile=? WHERE asset_id=? AND speaker_id=?", (display_name, json.dumps(profile), asset_id, speaker_id))
            db.execute("DELETE FROM segment_fts WHERE asset_id=? AND segment_id IN (SELECT segment_id FROM segments WHERE asset_id=? AND speaker_id=?)", (asset_id, asset_id, speaker_id))
            if self.trigram_available: db.execute("DELETE FROM segment_trigram WHERE asset_id=? AND segment_id IN (SELECT segment_id FROM segments WHERE asset_id=? AND speaker_id=?)", (asset_id, asset_id, speaker_id))
            for segment in db.execute("SELECT * FROM segments WHERE asset_id=? AND speaker_id=?", (asset_id, speaker_id)):
                db.execute("INSERT INTO segment_fts VALUES (?, ?, ?, ?, ?, ?, ?)", (segment["segment_id"], asset_id, segment["text"], segment["keywords"].replace('"', ''), segment["entities"].replace('"', ''), segment["topics"].replace('"', ''), display_name))
                if self.trigram_available: db.execute("INSERT INTO segment_trigram VALUES (?, ?, ?, ?, ?, ?)", (segment["segment_id"], asset_id, segment["text"], segment["keywords"].replace('"', ''), segment["entities"].replace('"', ''), display_name))

    @staticmethod
    def _fts_query(query: str, mode: str) -> str:
        tokens = [token.replace('"', '') for token in query.split() if token]
        if mode == "phrase": return f'"{" ".join(tokens)}"'
        if mode == "prefix": return " AND ".join(f'"{token}"*' for token in tokens)
        return " AND ".join(f'"{token}"' for token in tokens)

    @staticmethod
    def _matched_fields(row: dict, query: str, mode: str) -> list[str]:
        needle = normalise_term(query.rstrip("*"))
        def matches(value: str) -> bool:
            words = normalise_term(value).split()
            return any(word.startswith(needle) for word in words) if mode == "prefix" else needle in normalise_term(value)
        return [field for field, value in (("text", row["text"]), ("keywords", " ".join(row["keywords"])), ("entities", " ".join(row["entities"])), ("topics", " ".join(row["topics"])), ("speaker_name", row["speaker_name"])) if matches(value)]

    @staticmethod
    def _exact_match_type(fields: list[str], mode: str) -> str:
        if mode == "phrase":
            return "exact_phrase"
        if mode == "prefix":
            return "prefix"
        if mode == "substring":
            return "substring"
        for field, match_type in (("text", "exact_text"), ("keywords", "exact_keyword"), ("entities", "exact_entity"), ("topics", "exact_topic"), ("speaker_name", "exact_speaker")):
            if field in fields:
                return match_type
        return "exact_text"

    @staticmethod
    def _vocabulary(db: sqlite3.Connection, asset_id: str) -> list[SearchVocabularyTerm]:
        terms: dict[tuple[str, str], tuple[str, set[str]]] = {}
        rows = db.execute("""SELECT s.segment_id,s.keywords,s.entities,s.topics,p.display_name
            FROM segments s JOIN speakers p ON p.asset_id=s.asset_id AND p.speaker_id=s.speaker_id
            WHERE s.asset_id=?""", (asset_id,))
        for row in rows:
            values = (("keywords", json.loads(row["keywords"])), ("entities", json.loads(row["entities"])), ("topics", json.loads(row["topics"])), ("speaker_name", [row["display_name"]]))
            for field, entries in values:
                for display_term in entries:
                    term = normalise_term(str(display_term))
                    if not term:
                        continue
                    key = (term, field)
                    if key not in terms:
                        terms[key] = (str(display_term), set())
                    terms[key][1].add(row["segment_id"])
        return [SearchVocabularyTerm(term, display, field, sorted(segment_ids)) for (term, field), (display, segment_ids) in terms.items()]

    @staticmethod
    def _row_result(row: sqlite3.Row | dict, names: dict[str, str], query: str, mode: str) -> dict:
        result = {**dict(row), "speaker_name": names[row["speaker_id"]], "keywords": json.loads(row["keywords"]), "entities": json.loads(row["entities"]), "topics": json.loads(row["topics"]), "score": round(float(row["score"]), 4)}
        result["matched_fields"] = Storage._matched_fields(result, query, mode)
        result["match_type"] = Storage._exact_match_type(result["matched_fields"], mode)
        result["matched_term"] = query.rstrip("*").strip('"')
        result["similarity"] = 1.0
        result["is_exact"] = True
        return result

    def _fuzzy_results(self, db: sqlite3.Connection, asset_id: str, query: str) -> list[dict]:
        candidates = fuzzy_candidates(query, self._vocabulary(db, asset_id))
        if not candidates:
            return []
        rows = {row["segment_id"]: row for row in db.execute("""SELECT s.segment_id,s.text,s.speaker_id,s.start_seconds,s.end_seconds,s.keywords,s.entities,s.topics,0.0 AS score
            FROM segments s WHERE s.asset_id=?""", (asset_id,))}
        names = {row["speaker_id"]: row["display_name"] for row in db.execute("SELECT speaker_id, display_name FROM speakers WHERE asset_id=?", (asset_id,))}
        field_order = {"keywords": 0, "entities": 1, "topics": 2, "speaker_name": 3}
        found: dict[str, dict] = {}
        for candidate in candidates:
            for segment_id in candidate.term.segment_ids:
                row = rows.get(segment_id)
                if not row:
                    continue
                exact = candidate.similarity == 1.0
                match_type = ("exact_" if exact else "fuzzy_") + {"keywords": "keyword", "entities": "entity", "topics": "topic", "speaker_name": "speaker"}[candidate.term.field]
                result = found.get(segment_id)
                priority = (exact, candidate.similarity, -field_order[candidate.term.field])
                if result is None or priority > result["_priority"]:
                    result = self._row_result(row, names, query, "smart")
                    result.update({"score": 1.0 if exact else round(candidate.similarity * 0.70, 4), "match_type": match_type, "matched_term": candidate.term.display_term, "similarity": candidate.similarity, "is_exact": exact, "matched_fields": [candidate.term.field], "_priority": priority})
                    found[segment_id] = result
                elif candidate.term.field not in result["matched_fields"]:
                    result["matched_fields"].append(candidate.term.field)
        results = list(found.values())
        for result in results:
            result.pop("_priority")
        return sorted(results, key=lambda result: (not result["is_exact"], -result["similarity"], field_order[result["matched_fields"][0]], result["start_seconds"]))

    def search(self, asset_id: str, query: str, mode: str = "smart") -> list[dict]:
        if mode not in {"smart", "phrase", "prefix", "substring", "closest"}: raise ValueError("Unsupported search mode")
        if not query.strip():
            return []
        with self._connect() as db:
            if mode == "closest":
                return self._fuzzy_results(db, asset_id, query)
            if mode == "substring" and not self.trigram_available:
                rows = db.execute("""SELECT s.segment_id,s.text,s.speaker_id,s.start_seconds,s.end_seconds,s.keywords,s.entities,s.topics,0.0 AS score FROM segments s JOIN speakers p ON p.asset_id=s.asset_id AND p.speaker_id=s.speaker_id WHERE s.asset_id=? AND lower(s.text || ' ' || s.keywords || ' ' || s.entities || ' ' || s.topics || ' ' || p.display_name) LIKE '%' || lower(?) || '%' ORDER BY s.start_seconds LIMIT 50""", (asset_id, query)).fetchall()
            else:
                table = "segment_trigram" if mode == "substring" else "segment_fts"
                expression = query if mode == "substring" else self._fts_query(query, mode)
                weights = "1.0, 1.3, 1.3, 1.1, 1.1" if table == "segment_fts" else "1.0, 1.3, 1.3, 1.1"
                rows = db.execute(f"""SELECT f.segment_id, f.text, s.speaker_id, s.start_seconds, s.end_seconds, s.keywords, s.entities, s.topics, bm25({table}, {weights}) AS score FROM {table} f JOIN segments s ON s.segment_id=f.segment_id WHERE f.asset_id=? AND {table} MATCH ? ORDER BY score LIMIT 50""", (asset_id, expression)).fetchall()
            names = {row["speaker_id"]: row["display_name"] for row in db.execute("SELECT speaker_id, display_name FROM speakers WHERE asset_id=?", (asset_id,))}
            results = [self._row_result(row, names, query, mode) for row in rows]
            if mode == "smart" and len(results) < 2:
                exact_ids = {result["segment_id"] for result in results}
                results.extend(result for result in self._fuzzy_results(db, asset_id, query) if result["segment_id"] not in exact_ids)
        return results
