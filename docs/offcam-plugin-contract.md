# SpeechKit / SpeechLens OffCam plugin contract audit

Audit date: 2026-07-26. Source of truth is executable code in this repository and the default pytest suite. This document describes the standalone service only; it does not propose an OffCam pipeline integration. The approved OffCam placement is one compiled `SpeechKitPanel` in the existing right drawer activity rail.

## Classification used here

- **Implemented and verified**: exercised by the default test suite or the local running service during this audit.
- **Implemented but not externally verified**: present in code but its real Sarvam path is behind the opt-in integration test.
- **Partially implemented**: code exists but does not provide the complete external contract implied by the feature name.
- **Not implemented**: no executable route or behavior exists.

## 1. Repository and service identity

| Item | Current value |
| --- | --- |
| Repository root | `$REPOSITORY_ROOT` (resolved at audit runtime; the absolute user-specific path is reported outside this committed document) |
| Branch at audit start | `feature/speechlens-demo` |
| Commit at audit start | `9cebe7e508a0a55fd8534b7bb6aa0a8c958a6977` |
| Working tree at audit start | clean |
| Python used for audit | Python 3.11.14 |
| Package | `speechlens` 0.1.0 (`pyproject.toml`) |

**Implemented and verified:** from the repository root, after editable installation:

```bash
cd "$REPOSITORY_ROOT"
set -a; source .env; set +a
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```

The exact import path is `app:app`. Uvicorn defaults are host `127.0.0.1` and port `8000`; the documented command makes both explicit. `static/` is relative to the working directory, so this command must run from the repository root.

| Variable | Required | Default / use |
| --- | --- | --- |
| `SPEECHKIT_DATA_DIR` | optional | `./data`, resolved to an absolute path |
| `SPEECHKIT_FIXTURE_MODE` | optional | `1` enables deterministic synthetic Batch output without a Sarvam key or network call |
| `SARVAM_RUN_INTEGRATION_TESTS` | test-only optional | integration test skips unless `1` |
| `SPEECHKIT_INTEGRATION_AUDIO` | test-only optional | integration test skips unless set |

Live startup requires no environment API key. SpeechKit reads the Sarvam API key from the operating-system credential store at the start of a live upload. With `SPEECHKIT_FIXTURE_MODE=1`, no key is required and uploads use only a committed synthetic fixture; this is the supported OffCam contract-test mode.

| Endpoint | Status |
| --- | --- |
| Health endpoint | `GET /health`, verified `200`, typed `{"status":"ok","service":"speechkit","version":"0.1.0"}`; no Sarvam request |
| Root standalone UI | `GET /` (static HTML), verified `200`; not a health endpoint |
| OpenAPI | `GET /openapi.json`, verified `200` |
| Swagger UI | `GET /docs`, verified `200` |

### Provider credential configuration

**Implemented and verified:** SpeechKit owns a single global Sarvam credential in the operating-system credential store (`keyring` service `speechkit`, account `sarvam`). It does not read or persist the key in `.env`, SQLite, JSON, localStorage, artifact metadata, logs, public errors, responses, test fixtures, or project data.

| Method | Path | Request | Success response |
| --- | --- | --- | --- |
| `GET` | `/api/provider/config` | none | `{"provider":"sarvam","configured":true|false}` |
| `PUT` | `/api/provider/config` | JSON `{"api_key":"<non-blank string>"}` | `{"provider":"sarvam","configured":true}` |
| `DELETE` | `/api/provider/config` | none | `{"provider":"sarvam","configured":false}` |

The key is accepted only by `PUT` and is never returned. A credential-store access failure returns `500 credential_store_unavailable` using the public error envelope. For this approved demo the endpoints have no application authentication; they must remain localhost/internal-only or be reached only through an OffCam server-side proxy before production. OffCam must keep the key out of browser state beyond the active password form, display only **Configured** or **Not configured**, disable Analyse when `configured` is false, state that analysis uses real Sarvam credits, and treat explicit Analyse as the spending authorization.

## 2. Analysis request and ingestion

**Implemented and verified:** `POST /api/assets` is the only analysis-starting endpoint.

> **Current media ingestion requires multipart upload. Asset-reference and URL ingestion are not implemented.**

| Contract item | Current behavior |
| --- | --- |
| Content-Type | `multipart/form-data` |
| Headers | no application-specific headers; multipart boundary required by HTTP client |
| Path/query parameters | none |
| Body `file` | required uploaded file; OpenAPI represents it as an octet-stream part |
| Body `num_speakers` | optional integer form part; `1 <= value <= 20`; omission means `None` |
| Body `mode` | optional string form part; `transcribe` (default), `translate`, `verbatim`, `translit`, or `codemix` |
| Success | `200`, only after all synchronous processing completes |
| Success body | `{"asset_id":"<32-char UUID hex>","stage":"complete"}` |
| Validation | FastAPI `422` for missing/invalid form fields; `400` empty filename/file; `413` over size; `415` unsupported suffix; live `409 sarvam_not_configured` when no keychain key exists |

Accepted filename suffixes are `.aac`, `.avi`, `.flac`, `.m4a`, `.mkv`, `.mov`, `.mp3`, `.mp4`, `.mpeg`, `.mpg`, `.ogg`, `.opus`, `.wav`, and `.webm`. Filename suffix validation is followed by `ffprobe`; a deceptive or malformed file is rejected if it is unreadable, has no audio stream, or has no finite positive duration.

The service accepts **multipart media upload only**. It does not accept a raw request body, local filesystem path, public URL, private URL, signed URL, opaque OffCam asset reference, URL fetching, or custom URL authentication headers. It does not upload original MP3/MP4 directly to Sarvam: it always runs FFmpeg to extract mono 16 kHz PCM WAV, then submits the WAV to Sarvam Batch STT using the selected documented Saaras v3 mode.

Implemented SpeechKit limits: upload size is 500 MiB (`Settings.max_upload_bytes`); there is no maximum media duration beyond positive finite duration; no HTTP request timeout is configured by FastAPI/Uvicorn. Internal timeouts are ffprobe 30 seconds, FFmpeg 300 seconds, Sarvam SDK client 60 seconds, and Batch wait 1,800 seconds. These are not Sarvam upstream limits. Sarvam limits are not encoded or verified by this service.

```bash
curl -X POST http://127.0.0.1:8000/api/assets \
  -F 'file=@./recording.mp4;type=video/mp4' \
  -F 'num_speakers=2' \
  -F 'mode=translit'
```

## 3. Analysis lifecycle

**Implemented and verified (code/tests):** processing is synchronous inside the multipart request. It is neither an in-process background task nor a queued job. The async FastAPI route directly calls the blocking service function, so a single-worker server cannot reliably service status polling while that request is running. The initial response is the final success response above; there is no accepted/queued response.

The generated SpeechKit asset ID is a UUID hex string. No execution ID or analysis ID exists. Sarvam's Batch `job_id` is stored in artifact metadata only; Sarvam's `request_id` is also metadata only. Neither is returned by the upload response or status response.

Exact storage status values written by code are:

```text
uploaded → extracting_audio → submitting → normalising → complete
                                      └──────────────→ failed
```

`transcribing` and `indexing` are not written. Search indexing happens inside `save_artifact` without a distinct stage. `GET /api/assets/{asset_id}` and `GET /api/assets/{asset_id}/status` are aliases. On success their untyped JSON is the SQLite `assets` row:

```json
{
  "asset_id": "string",
  "filename": "string",
  "duration_seconds": 0.0,
  "status": "uploaded|extracting_audio|submitting|normalising|complete|failed",
  "error": "string or null",
  "metadata": "JSON-encoded string"
}
```

It returns a stable `404` public error envelope with code `asset_not_found` only for an unknown ID. `complete` is the sole terminal success state; `failed` is the sole terminal failure state. There is stage-name progress only, no percentage.

**Polling recommendation constrained by current behavior:** do not poll during the synchronous upload request. After it returns an asset ID, one status/artifact refresh is sufficient. If a future deployment uses multiple workers, poll only while the SpeechKit drawer panel is visible, start at 1 second and back off to 5 seconds, stop at `complete`/`failed`, and resume on panel reopen. This is a client convention, not a present server feature.

### Idempotency, retry, cancellation

| Behavior | Audit result |
| --- | --- |
| Idempotency key | **Not implemented** |
| Media hash / reuse | **Not implemented** |
| Identity | generated SpeechKit `asset_id` only; filename is not identity |
| Same media twice | creates distinct local asset directories and duplicate Sarvam jobs |
| Retry API | **Not implemented** |
| Retry semantics | a client can submit again; that creates a new SpeechKit record and Sarvam job |
| Sarvam request retries | create/upload/start retry 408, 429, 500, 503 and `ConnectionError`, up to five attempts with capped exponential delay plus jitter; poll/download are not retried by that helper |
| Cancellation API / Sarvam cancellation | **Not implemented** |
| Stop polling | frontend may stop polling only; it cannot stop the active request/job |

The `jobs` SQLite table exists but is never written or read: it is **partially implemented**, not an externally usable job lifecycle.

## 4. Exact `speechkit.v1` artifact

**Implemented and verified:** `GET /api/assets/{asset_id}/artifact` returns `application/json`, `200`, only when the stored asset status is `complete`. It has one string path parameter. Unknown and incomplete/failed assets both return `404` with public error code `artifact_not_found`; callers cannot distinguish those cases from this endpoint.

Every successful response constructs these top-level keys:

| Key | Type / nullability | Units / source |
| --- | --- | --- |
| `schema_version` | string, non-null; always `speechkit.v1` | storage output literal |
| `asset_id` | string, non-null | SpeechKit UUID hex |
| `filename` | string, non-null | sanitized uploaded basename |
| `duration_seconds` | number, non-null | ffprobe duration, seconds |
| `provider` | string, non-null; `sarvam` | storage output literal |
| `model` | string, non-null; `saaras:v3` | storage output literal |
| `language_code` | string or null | Sarvam output copied into metadata |
| `speakers` | array | persisted profiles |
| `segments` | array ordered by `start_seconds` ascending | persisted turns |
| `metadata` | object | persisted metadata JSON decoded |

Each `segments[]` object has these non-null fields: `segment_id` (string), `asset_id` (string), `speaker_id` (string), `speaker_name` (string), `text` (string), `start_seconds` (number, seconds), `end_seconds` (number, seconds), `keywords` (string array), `entities` (string array), and `topics` (string array). Blank, non-finite, negative-start, and non-positive-duration Sarvam entries are discarded before persistence.

Each `speakers[]` object has: `speaker_id` and `display_name` (strings); `speaking_seconds`, `speaking_percentage`, `average_turn_seconds`, and `longest_turn_seconds` (numbers; seconds except percentage); `word_count`, `turn_count`, and `questions_asked` (integers); plus `keywords`, `entities`, and `representative_quotes` (string arrays). Quotes are text only: no segment IDs, timestamps, or scores.

Metadata is intentionally untyped and has these current normalisation keys: `sarvam_job_id` (string), `sarvam_request_id` (Sarvam value or null), `language_probability` (Sarvam value or null), `sarvam_timestamps` (raw Sarvam value or null), `file_failures` (array), `sarvam_response_metadata` (currently an `audio_mime` entry only when present), and `estimated_cost_inr` (number). The service adds `language_code` and `sarvam_mode` (the submitted mode).

Internal metadata retains `media_path` so `GET /api/assets/{asset_id}/media` can stream the original file, but all public asset and artifact responses remove it. Public `file_failures` are reduced to `{"code":"provider_file_failed"}` entries and persisted error text is replaced with a generic safe failure message. API keys, signed URLs, raw audio hash, raw provider exceptions, headers, tracebacks, and absolute paths are not exported.

### Fabrication policy

| Field | Current source / unavailable behavior |
| --- | --- |
| speakers / turns / timestamps | copied from valid `diarized_transcript.entries`; no turn is invented; missing valid entries makes analysis fail |
| `speaker_id` | Sarvam ID normalized to `speaker_<id>` |
| `speaker_name` | deterministic placeholder `Speaker <raw-id>` until user rename; it is not human identification |
| language / probability / raw timestamps | copied from Sarvam when present; language is null when absent |
| keywords / entities / topics | deterministic Python extraction from segment text; empty arrays when none; topics are the first three derived keywords |
| representative quotes | deterministic text-only selection from existing turns; empty array when no turns |
| confidence | not present / not fabricated |

Thus SpeechKit does not fabricate unavailable diarised speakers, timestamps, language, or confidence. It does create placeholder speaker display labels and deterministic intelligence, which must not be represented as provider-supplied facts.

## 5. Search contract

**Implemented and verified:** `GET /api/assets/{asset_id}/search?q=<string>&mode=<mode>`.

| Parameter | Type / required | Values |
| --- | --- | --- |
| `asset_id` | path string, required | SpeechKit asset ID; unknown ID currently yields `200` with an empty result set |
| `q` | query string, required | FastAPI `min_length=1`; whitespace-only returns no results after validation |
| `mode` | optional query string | `smart` (default), `phrase`, `prefix`, `substring`, `closest` |

`closest` is the API value; the standalone UI label is **Closest keyword**. Response shape is:

```json
{
  "query": "mutatin",
  "mode": "closest",
  "elapsed_ms": 1.234,
  "results": [{
    "segment_id": "string",
    "speaker_id": "string",
    "speaker_name": "string",
    "start_seconds": 42.3,
    "end_seconds": 49.8,
    "text": "string",
    "keywords": ["string"],
    "entities": ["string"],
    "topics": ["string"],
    "score": 0.6533,
    "matched_fields": ["keywords"],
    "match_type": "fuzzy_keyword",
    "matched_term": "mutating",
    "similarity": 0.9333,
    "is_exact": false
  }]
}
```

There is **no `asset_id` inside a result**. Timestamps are seconds. `elapsed_ms` is process-local wall-clock time around `Storage.search`, rounded to three decimals. `matched_fields` may contain `text`, `keywords`, `entities`, `topics`, and `speaker_name`. Match types are `exact_phrase`, `exact_text`, `exact_keyword`, `exact_entity`, `exact_topic`, `exact_speaker`, `prefix`, `substring`, `fuzzy_keyword`, `fuzzy_entity`, `fuzzy_topic`, and `fuzzy_speaker`.

| Mode | Actual implementation |
| --- | --- |
| `smart` | standard FTS5 with BM25 weights text 1.0, keywords 1.3, entities 1.3, topics 1.1, speaker name 1.1; when fewer than two FTS results, append non-duplicate close-token metadata results |
| `phrase` | quoted FTS5 phrase query |
| `prefix` | FTS5 prefix query for all whitespace tokens |
| `substring` | trigram FTS5 when available; otherwise parameterised case-insensitive SQLite `LIKE` over text, keywords, entities, topics, and speaker name |
| `closest` | RapidFuzz `WRatio` over structured vocabulary only; not semantic search |

FTS branches use `ORDER BY bm25(...)` ascending (lower BM25 is better) with a SQL `LIMIT 50`. `LIKE` returns timestamp-ascending with `LIMIT 50`. Fuzzy results use `score = similarity * 0.70` (or `1.0` for exact vocabulary equality), sort exact before fuzzy, then similarity descending, field priority keywords → entities → topics → speaker name, then timestamp ascending. Smart returns lexical FTS results first and then fuzzy additions; scores are therefore mode-dependent and not globally comparable. SQL FTS ties have no explicit stable tie-breaker. Closest expansion has no result-count limit after its five vocabulary candidates. There is no pagination or caller-provided limit.

Closest vocabulary is rebuilt from canonical segment keywords, entities, topics, and current speaker names. It never fuzzily searches raw transcript tokens. Normalisation case-folds and trims terms while preserving internal punctuation. Query length <=3 disables fuzzy matching; 4–5 requires similarity >=0.85; >=6 requires >=0.78; at most five vocabulary candidates are expanded; duplicate segment IDs are merged.

Examples:

```text
GET /api/assets/<asset>/search?q=terraform&mode=smart
GET /api/assets/<asset>/search?q=customer%20managed&mode=phrase
GET /api/assets/<asset>/search?q=deploy*&mode=prefix
GET /api/assets/<asset>/search?q=ploym&mode=substring
GET /api/assets/<asset>/search?q=mutatin&mode=closest
```

All five return the same top-level response shape. Representative mode-specific result facts are:

| Mode | Representative response fragment |
| --- | --- |
| `smart` | `{"query":"terraform","mode":"smart","results":[{"match_type":"exact_text","similarity":1.0,"is_exact":true}]}` |
| `phrase` | `{"query":"customer managed","mode":"phrase","results":[{"match_type":"exact_phrase","similarity":1.0,"is_exact":true}]}` |
| `prefix` | `{"query":"deploy*","mode":"prefix","results":[{"match_type":"prefix","similarity":1.0,"is_exact":true}]}` |
| `substring` | `{"query":"ploym","mode":"substring","results":[{"match_type":"substring","similarity":1.0,"is_exact":true}]}` |
| `closest` | `{"query":"mutatin","mode":"closest","results":[{"matched_term":"mutating","match_type":"fuzzy_keyword","similarity":0.9333,"is_exact":false}]}` |

## 6. Speaker rename

**Implemented and verified in storage tests:** `PATCH /api/assets/{asset_id}/speakers/{speaker_id}` with path strings and JSON body `{"display_name":"New name"}`. A successful rename returns `200 {"ok":true}`. `display_name` is required by Pydantic but has no length or non-empty validation; route code strips whitespace, so an all-whitespace value can become an empty name. Missing/invalid JSON gives the structured `422 invalid_request` envelope; an unknown speaker (including unknown asset) gives `404 speaker_not_found`.

```bash
curl -X PATCH http://127.0.0.1:8000/api/assets/<asset>/speakers/speaker_0 \
  -H 'content-type: application/json' \
  -d '{"display_name":"Alex"}'
```

Rename updates canonical speaker storage and its stored profile, artifact output, standalone transcript output (which is embedded in artifact), standard FTS5, trigram FTS5 when available, and search results. Fuzzy vocabulary is rebuilt from canonical records per search, so old names disappear unless they occur elsewhere. SQLite persistence means it survives service restart. **Speaker merge is not implemented.**

## 7. Error contract

All handled public errors use one stable envelope. `details` is currently always an empty object and no public error exposes a provider request ID.

```json
{"error":{"code":"...","message":"...","retryable":false,"details":{}}}
```

| Situation | Runtime status / response | Retry signal |
| --- | --- | --- |
| unknown asset/status | 404 `asset_not_found` | false |
| missing/incomplete artifact | 404 `artifact_not_found` | false |
| media not found | 404 `media_not_found` | false |
| malformed request / invalid mode | 422 `invalid_request` | false |
| empty/unsupported upload | 400/415 `invalid_upload` | false |
| oversize upload | 413 `upload_too_large` | false |
| no audio | 422 `media_no_audio` | false |
| FFmpeg extraction failure | 422 `ffmpeg_failed` | false |
| malformed media | 422 `invalid_media` | false |
| no usable diarised speech | 422 `no_speech` | false |
| no stored Sarvam key | 409 `sarvam_not_configured` | false |
| OS credential store unavailable | 500 `credential_store_unavailable` | false |
| Sarvam authentication | 502 `sarvam_authentication` | false |
| Sarvam rate limiting | 503 `sarvam_rate_limited` | true |
| Sarvam timeout | 504 `provider_timeout` | true |
| unusable Sarvam response | 502 `provider_response_invalid` | true |
| other Sarvam error | 502 `provider_error` | true |
| unknown speaker | 404 `speaker_not_found` | false |
| SQLite failure | 500 `storage_failure` | false |
| unexpected server failure | 500 `internal_error` | true |

Sarvam 429/500/503/408 and connection failures are retried only around create/upload/start; authentication 403, 413, and 422 are not retried. A partial Batch failure is accepted when at least one file succeeds; public artifact metadata retains only safe file-failure codes. The normal path does not expose API keys, request headers, signed URLs, tracebacks, raw provider exceptions, raw transcript text, or absolute local paths in errors or JSON responses.

## 8. Storage and identity

| Item | Current implementation |
| --- | --- |
| Configured data root | `SPEECHKIT_DATA_DIR`, default resolved `./data` |
| SQLite | `<data-dir>/speechlens.sqlite` |
| Per-asset directory | `<data-dir>/<speechkit-asset-id>/` |
| Original media | retained as `<asset-dir>/<sanitized-filename>` |
| Extracted WAV | retained as `<asset-dir>/audio.wav` |
| Sarvam output | retained as `<asset-dir>/sarvam-output/*.json` |
| Temporary upload | OS temporary file; removed by route only if it was not moved |

Persisted database tables: `assets` (status/error/metadata), `speakers` (profile JSON), `segments` (canonical turns), and `jobs` (defined but unused). FTS tables: `segment_fts` (weighted lexical fields) and, where SQLite supports it, `segment_trigram` (substring text/keywords/entities/speaker name). There is no cleanup endpoint, delete-one-asset operation, artifact deletion, source deletion, project cleanup, retention policy, or garbage collection. Original media, WAV, raw downloaded output, and SQLite rows survive success/failure and restart until manual deletion.

SpeechKit does not know `project_id`; all storage is keyed by generated SpeechKit `asset_id`. Filename is display metadata, not identity. There is no content hash. The safest current bridge mapping is an OffCam-owned mapping table of `(offcam project_id, offcam asset_id) -> speechkit asset_id`, with no direct exposure of SpeechKit's stored `media_path`. Identical OffCam asset IDs in different projects can collide in an OffCam mapping that omits `project_id`; SpeechKit itself has no project namespace.

Browser refresh and restart preserve completed data while the data directory remains. Disable/re-enable and project switching have no SpeechKit implementation or semantics; only an external bridge can define them.

## 9. Frontend reuse

| File / unit | Classification |
| --- | --- |
| `static/index.html` | standalone application shell, page layout, upload form (including the five Sarvam mode choices), player, raw artifact panel; not directly reusable as a drawer component |
| `static/app.js` `seek`, `time`, `tags`, `resultCard` | reusable plain JavaScript behavior, but tightly coupled DOM rendering |
| `static/app.js` `refresh`, `rename`, `search` | API client logic coupled to global DOM state and relative URLs |
| `static/app.js` `render` and event wiring | tightly coupled DOM code / standalone shell |
| `static/styles.css` | standalone global CSS and full-page layout |

The frontend is plain JavaScript, HTML, CSS, and browser-native `fetch`, `Blob`, `URL.createObjectURL`, and `<audio>` APIs. It has no React, TypeScript, npm package, reusable React package, or third-party UI dependency. OffCam cannot directly import a current frontend component; it must adapt API behavior and data shapes into a native compiled React `SpeechKitPanel` registered in the existing panel registry. Remove the standalone header, page shell, upload page framing, standalone player layout, global CSS/reset/layout assumptions, and all global `document.querySelector` state. Keep only behavior-level concepts: upload form data, artifact rendering, rename request, search request, result timestamp, and JSON export.

The panel must remain inside the approved right drawer; this audit does not recommend global search, CaptionKit, timeline, monitor, export, or other OffCam integration.

## 10. Testing and fixtures

From repository root:

```bash
.venv/bin/python -m pytest -q
```

Latest audit result: **53 passed, 1 skipped, 0 failed**. Default tests require no Sarvam key, make no network or paid Sarvam calls, do not require FFmpeg, and use temporary SQLite databases where storage is exercised.

The formal fixture-backed service mode is implemented and tested. It uses committed synthetic output from `src/speechkit/fixtures/offcam_batch_output.json`; it makes no network request and needs no Sarvam key.

```bash
SPEECHKIT_FIXTURE_MODE=1 \
SPEECHKIT_DATA_DIR=./data-fixture \
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```

Upload a supported filename to create deterministic `complete` analysis, then use normal status, artifact, search, rename, and export endpoints. No asset is preloaded; the ID is returned by the upload response.

Real Sarvam is opt-in:

```bash
SARVAM_API_KEY=... \
SARVAM_RUN_INTEGRATION_TESTS=1 \
SPEECHKIT_INTEGRATION_AUDIO=/path/to/non-sensitive.wav \
.venv/bin/python -m pytest -m integration
```

The marker is `integration`; it skips by default. It asserts only non-empty `job_id` and `output["transcript"]`, not exact wording. It warns through its skip reason that it spends credits; it does not print an estimate and has no cleanup. Committed safe fixtures are `tests/fixtures/sarvam_batch_output.json` and `tests/fixtures/sarvam_batch_observed_sanitized.json`. Git ignores `.env`, `data/*`, virtual environments, and bytecode; audit inspection found no committed private media, private transcript, API key, database, signed URL, or user-specific absolute path in these new contract files.

## Documentation/code disagreements

| Documentation claim | Executable evidence |
| --- | --- |
| README describes a lifecycle including indexing | code writes no `indexing` status; indexing happens inside `save_artifact` |
| README says storage persists jobs | `jobs` table is created but no code persists or reads a job |
| README calls raw timing "timestamp chunks" | normaliser preserves any `timestamps` shape; the committed observed fixture uses `timestamps.words`, not chunks |
| README says the integration marker is reserved/absent until fixture/key is supplied | `tests/test_integration.py` is present and uses environment-gated real audio/key inputs |
| Earlier README revisions said `SARVAM_API_KEY` was required at startup | current live startup uses no environment key; a keychain credential is required only to submit a live analysis |
| README states price/billing semantics | no pricing or billing behavior is validated by executable code/tests |

## 11. Generated OpenAPI

`docs/offcam-plugin-openapi.json` was fetched from the running service's `GET /openapi.json`; it was not hand-authored. It exposes eleven operations across nine paths, including typed `/health` and provider credential configuration, plus request validation for file upload, speaker count, search mode, and rename body. It is incomplete for OffCam client generation because most route responses are untyped dictionaries, `FileResponse` lacks a media response schema, and no response models declare the shared error envelope or artifact/status/search structures.

## 12. Readiness verdict

| Contract area | Ready | Partial | Missing | OffCam blocker |
| --- | ---: | ---: | ---: | ---: |
| Service startup | ✓ |  |  |  |
| Health endpoint | ✓ |  |  |  |
| Credential configuration | ✓ |  |  |  |
| Media ingestion | ✓ |  |  | ✓ |
| Analysis lifecycle |  | ✓ |  | ✓ |
| Artifact schema |  | ✓ |  | ✓ |
| Search | ✓ |  |  |  |
| Speaker rename | ✓ |  |  |  |
| Error envelope | ✓ |  |  |  |
| Storage identity |  | ✓ |  | ✓ |
| Frontend reuse |  | ✓ |  |  |
| Fixture testing | ✓ |  |  |  |

**YES, WITH LIMITATIONS — the isolated bridge still needs project/asset identity namespacing and secure OffCam asset-reference ingestion; current ingestion remains multipart upload only.**

Smallest next SpeechKit slice: add a bridge-only request contract that accepts validated `{project_id, asset_id}` from an OffCam backend resolver (not browser paths/URLs) and persists the pair alongside SpeechKit IDs. No global OffCam integration is required.
