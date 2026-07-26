# SpeechLens implementation guide

This document explains the current implementation of SpeechLens and its reusable `speechkit` package. It is a guide to the executable service, not a promise of production-scale features.

## Purpose and boundaries

SpeechLens is a local, speaker-aware conversation-search demo. It accepts a media upload, uses Sarvam Batch STT, stores the normalised result locally, and presents a plain-browser interface for inspection and timestamp playback.

The package boundary is intentional:

```text
FastAPI + static SpeechLens UI
             |
       speechkit service
             |
Sarvam provider | media tools | SQLite storage | search
```

Only `src/speechkit/sarvam_provider.py` imports and uses the Sarvam SDK. Sarvam response dictionaries are normalised before the rest of the application sees them. No Sarvam SDK object crosses into the storage, UI, or export paths.

## Source layout

| Path | Responsibility |
| --- | --- |
| `app.py` | FastAPI routes, upload boundary, public error envelope, static UI mount. |
| `src/speechkit/config.py` | Environment-backed settings and fixture-mode switch. |
| `src/speechkit/media.py` | Upload-name validation, ffprobe inspection, FFmpeg WAV extraction. |
| `src/speechkit/sarvam_provider.py` | Sarvam Batch lifecycle and transient SDK retry handling. |
| `src/speechkit/fixture_provider.py` | Offline deterministic Batch substitute for tests and demos. |
| `src/speechkit/normalize.py` | Sarvam response to canonical `SpeechArtifact` conversion. |
| `src/speechkit/intelligence.py` | Deterministic keywords, entities, topics, metrics, and quotes. |
| `src/speechkit/storage.py` | SQLite canonical records, FTS indexes, artifact reconstruction, redaction. |
| `src/speechkit/fuzzy.py` | RapidFuzz metadata vocabulary and close-token matching. |
| `src/speechkit/service.py` | Analysis orchestration and lifecycle stages. |
| `static/` | Browser-native HTML, CSS, and JavaScript application shell. |

## Live analysis path

`POST /api/assets` accepts one multipart file, optional `num_speakers` from 1 to 20, and a mode. Processing is synchronous in the request for this demo.

```text
upload
  → validate suffix and size
  → move original media into a per-asset directory
  → ffprobe verifies a positive duration and audio stream
  → FFmpeg produces mono 16 kHz WAV
  → Sarvam creates a Batch job, uploads, starts, waits, and downloads output
  → normalise diarised entries and preserve raw timestamp metadata
  → derive speaker intelligence
  → persist artifact, segments, profiles, and FTS records
  → return {asset_id, stage: "complete"}
```

The stored status values are `uploaded`, `extracting_audio`, `submitting`, `normalising`, `complete`, and `failed`. There is no background queue, cancellation endpoint, retry endpoint, idempotency key, webhook, or progress percentage. A duplicate upload creates a distinct asset and can create another Sarvam job.

### Sarvam configuration

The provider creates a Batch request with:

```text
model = saaras:v3
language_code = unknown
with_diarization = true
with_timestamps = true
```

The selectable mode is one of `transcribe`, `translate`, `verbatim`, `translit`, or `codemix`; it is passed through without a SpeechLens reinterpretation. The selected value is recorded as `artifact.metadata.sarvam_mode`.

The provider retries only create/upload/start failures that look transient: 408, 429, 500, 503, or `ConnectionError`. It uses capped exponential backoff with jitter. Authentication and other non-retryable status errors are not retried.

## Normalisation and artifact

`normalize_batch_output` treats `diarized_transcript.entries` as the canonical source of speaker turns. Each valid entry provides transcript text, speaker identifier, `start_time_seconds`, and `end_time_seconds`. Invalid, blank, negative, or non-positive entries are discarded; no usable segments produce a `no_speech` failure instead of fabricated data.

Sarvam timestamp data remains raw under `metadata.sarvam_timestamps`; this slice does not advertise word-level timestamps. The exported provider-neutral format is `speechkit.v1` and includes:

- Recording identity and duration.
- Provider, model, and detected language when available.
- Recording-local speaker profiles.
- Ordered diarised `SpeechSegment` records in seconds.
- Provider request/job information, raw timestamp representation, safe file-failure codes, and an estimated cost.

The public artifact deliberately removes the internal `media_path`. It retains only information safe to send to a browser. The media endpoint looks up the internal path itself and never returns it in JSON.

## Deterministic speaker intelligence

SpeechLens does not call an LLM at runtime. It derives all intelligence from existing transcript turns:

- Duration, percentage, turn count, word count, and questions are simple aggregates.
- Keywords use normalised frequency-based token and useful-bigram selection.
- Entities use lightweight casing/acronym/technical-name heuristics.
- Topics are derived from extracted keywords.
- Representative quotes prefer substantive turns.

These fields are deterministic derived metadata, not Sarvam claims and not human identity. Speaker IDs identify a diarised voice within one recording only.

## Storage and search

SQLite is the canonical store. The service has asset, speaker, segment, and job tables plus:

- `segment_fts`: standard FTS5 for text, keywords, entities, topics, and speaker names.
- `segment_trigram`: optional FTS5 trigram index for arbitrary substring search.

When SQLite lacks the trigram tokenizer, substring mode explicitly uses a parameterised small-data `LIKE` fallback. Standard FTS5 remains the default search path.

Search modes are:

| API mode | Mechanism |
| --- | --- |
| `smart` | Weighted BM25 FTS5, then close-token fallback only when fewer than two lexical results exist. |
| `phrase` | Parameterised FTS5 phrase query. |
| `prefix` | Parameterised FTS5 prefix query. |
| `substring` | Trigram FTS5 or explicit `LIKE` fallback. |
| `closest` | RapidFuzz `WRatio` over keywords, entities, topics, and active speaker names. |

Close-token matching does not scan every raw transcript token. It has a minimum query length of four and query-length-aware thresholds. Exact result categories always rank ahead of close matches. Fuzzy results identify the matched indexed term, field, similarity, and `is_exact: false` so callers cannot mistake them for semantic matches.

Renaming a speaker updates canonical speaker data and rebuilds that speaker's FTS/trigram rows. Fuzzy vocabulary is reconstructed from canonical records on each query, so the old display name stops being searchable unless it exists elsewhere.

## Public API and errors

The health endpoint is independent of Sarvam:

```text
GET /health
```

All application errors use this JSON envelope:

```json
{"error":{"code":"...","message":"...","retryable":false,"details":{}}}
```

Public errors are intentionally redacted. They do not expose local paths, API keys, headers, signed URLs, provider exception strings, or tracebacks. Representative codes include `invalid_upload`, `media_no_audio`, `ffmpeg_failed`, `sarvam_authentication`, `sarvam_rate_limited`, `provider_timeout`, `asset_not_found`, `artifact_not_found`, `speaker_not_found`, and `storage_failure`.

For endpoint parameters and generated request schemas, use [offcam-plugin-openapi.json](offcam-plugin-openapi.json). For the fuller bridge readiness assessment, use [offcam-plugin-contract.md](offcam-plugin-contract.md).

## Fixture mode

Set `SPEECHKIT_FIXTURE_MODE=1` to replace live Sarvam work, ffprobe, and FFmpeg extraction with a small committed synthetic Batch response. Fixture mode accepts supported upload filenames and executes the same service, normalisation, persistence, search, rename, and export code paths. It is suitable for repeatable UI demos and integration tests; it never represents a real transcript.

```bash
SPEECHKIT_FIXTURE_MODE=1 \
SPEECHKIT_DATA_DIR=./data-fixture \
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```

## Testing and maintenance

Run the default safe suite:

```bash
.venv/bin/python -m pytest -q
```

It uses mocks, temporary SQLite databases, and committed synthetic fixtures. The opt-in `integration` marker is the only path intended to call Sarvam; it requires `SARVAM_API_KEY=...`, `SARVAM_RUN_INTEGRATION_TESTS=1`, and `SPEECHKIT_INTEGRATION_AUDIO=/path/to/short.wav`.

Keep generated data out of Git. `.env`, local `data/`, recordings, extracted WAV files, raw Sarvam downloads, SQLite databases, and signed URLs are runtime-only material.

## OffCam boundary

The current service is a standalone multipart-upload tool. It does not know an OffCam `project_id`, accept opaque OffCam asset references, or resolve private source media. An OffCam bridge should keep `SARVAM_API_KEY` server-side, map `(project_id, asset_id)` to a SpeechKit asset, and consume only the public API or `speechkit.v1` artifact.

The isolated right-drawer integration contract and its remaining limitations are documented in [offcam-plugin-contract.md](offcam-plugin-contract.md).
