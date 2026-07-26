# SpeechLens

SpeechLens is a standalone demo of searchable, speaker-aware conversations. Upload an audio or video conversation, let Sarvam Batch STT identify the turns, rename speakers, search what was said, and seek the original media to a match. The reusable `speechkit` package exports a provider-neutral `speechkit.v1` artifact for a later OffCam adapter.

## Run

Requirements: Python 3.11+, FFmpeg and ffprobe on `PATH`, and a Sarvam API key.

```bash
cp .env.example .env
# Set SARVAM_API_KEY in .env or export it in your shell.
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -e '.[dev]'
set -a; source .env; set +a
.venv/bin/uvicorn app:app --reload
```

For deterministic local/OffCam contract testing without a Sarvam key or network access:

```bash
SPEECHKIT_FIXTURE_MODE=1 SPEECHKIT_DATA_DIR=./data-fixture \
  .venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```

Fixture mode accepts normal supported uploads but uses committed synthetic Batch output. It is not a real transcription mode.

Open `http://127.0.0.1:8000`, upload a conversation, optionally set its expected speaker count, then rename/search/export from the completed view. FFmpeg converts the source to mono 16 kHz WAV while the original remains available for browser playback.

SpeechLens rejects empty and unsupported uploads before they reach Sarvam, checks that media has a finite duration and an audio stream, and marks the asset failed when FFmpeg, Batch STT, or transcript normalisation fails. A valid recording with no usable diarised speech is reported as a failed analysis with retry guidance; malformed Sarvam responses are surfaced as controlled provider errors rather than crashing the server.

See [demo setup](docs/setup.md) for prerequisites, secure local hosting, verification steps, and the opt-in real Sarvam test.

## Architecture

`sarvam_provider.py` contains all SDK usage. `normalize.py` maps `diarized_transcript.entries` to canonical `SpeechSegment`s; Sarvam chunk timestamps remain under `metadata.sarvam_timestamps`. `storage.py` persists assets, jobs, speakers, segments and an SQLite FTS5 index. No Sarvam SDK object escapes the provider module.

The batch call uses `saaras:v3`, `language_code="unknown"`, `with_diarization=True`, and timestamp chunks. The upload UI and API support Sarvam Batch modes `transcribe` (default), `translate`, `verbatim`, `translit` (Roman transliteration), and `codemix`; the selected mode is retained as `metadata.sarvam_mode`. The lifecycle is create job, upload, start, wait, inspect per-file results, download JSON output, then normalise. It has no cancellation, deletion, retry-in-place, idempotency, webhook, streaming, vector search, or paid-provider fallback.

Sarvam publishes ₹45/hour for STT with diarisation, billed per second. SpeechLens estimates `media_duration / 3600 * 45` INR before metadata is persisted; billing semantics for failed jobs are not documented. Speaker IDs are recording-local labels, not cross-recording identities.

## Search modes

Standard SQLite FTS5 covers transcript tokens, quoted phrases, prefixes, and indexed keywords, entities, topics, and speaker names. Trigram FTS5 handles arbitrary middle-of-token substring searches. RapidFuzz supplies the `Closest keyword` mode and the Smart-mode fallback: it compares a query only with indexed structured metadata, not every transcript token.

For example, `mutatin` can find the indexed keyword `mutating`. This is fuzzy token similarity, not semantic or conceptual search: `genetic transformation` will not be inferred as `mutating DNA`. Embeddings, synonyms, and semantic similarity are intentionally unsupported.

## Tests

```bash
.venv/bin/python -m pytest -q
SARVAM_RUN_INTEGRATION_TESTS=1 .venv/bin/python -m pytest -m integration
```

The default suite has no network/API-key dependency and uses [`tests/fixtures/sarvam_batch_output.json`](tests/fixtures/sarvam_batch_output.json), a documented Sarvam Batch response shape. The integration marker is reserved for a short real WAV and is intentionally absent until a non-sensitive fixture/key is supplied.

## `speechkit.v1` output

```json
{"schema_version":"speechkit.v1","provider":"sarvam","model":"saaras:v3","speakers":[{"speaker_id":"speaker_0","display_name":"Speaker 0"}],"segments":[{"speaker_id":"speaker_0","start_seconds":0.01,"end_seconds":2.5,"text":"Hello"}]}
```

An OffCam integration should depend only on this artifact and the `SpeechSegment`/`SpeechArtifact` models, not this web application or the Sarvam SDK.
