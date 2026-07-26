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

Open `http://127.0.0.1:8000`, upload a conversation, optionally set its expected speaker count, then rename/search/export from the completed view. FFmpeg converts the source to mono 16 kHz WAV while the original remains available for browser playback.

## Architecture

`sarvam_provider.py` contains all SDK usage. `normalize.py` maps `diarized_transcript.entries` to canonical `SpeechSegment`s; Sarvam chunk timestamps remain under `metadata.sarvam_timestamps`. `storage.py` persists assets, jobs, speakers, segments and an SQLite FTS5 index. No Sarvam SDK object escapes the provider module.

The batch call uses `saaras:v3`, `mode="transcribe"`, `language_code="unknown"`, `with_diarization=True`, and timestamp chunks. The lifecycle is create job, upload, start, wait, inspect per-file results, download JSON output, then normalise. It has no cancellation, deletion, retry-in-place, idempotency, webhook, streaming, translation UI, vector search, or paid-provider fallback.

Sarvam publishes ₹45/hour for STT with diarisation, billed per second. SpeechLens estimates `media_duration / 3600 * 45` INR before metadata is persisted; billing semantics for failed jobs are not documented. Speaker IDs are recording-local labels, not cross-recording identities.

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
