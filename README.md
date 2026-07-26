# SpeechLens

SpeechLens is a standalone, local web demo for analysing a conversation. Upload an audio or video recording, let Sarvam Batch STT diarise it, inspect speaker turns and deterministic speaker intelligence, search what was said, and play from the matching timestamp.

The reusable Python package is `speechkit`. It produces a provider-neutral `speechkit.v1` JSON artifact so an application such as OffCam can later integrate the service without importing Sarvam SDK objects.

## What it demonstrates

- Audio and video upload with safe filename and size checks.
- FFprobe inspection and FFmpeg conversion to mono 16 kHz WAV.
- Sarvam Batch STT using `saaras:v3`, diarisation, and timestamped turns.
- Speaker metrics: speaking time, turn and word counts, questions, keywords, entities, and representative quotes.
- SQLite persistence and FTS5 search over transcript text and indexed metadata.
- Phrase, prefix, substring, and typo-tolerant close-token search.
- Speaker renaming, native media seeking, and `speechkit.v1` export.
- A deterministic offline fixture mode for demos and OffCam contract tests.

It is deliberately not a production deployment, streaming client, translation UI, semantic search system, or cross-recording speaker-identification system.

## Quick start: offline fixture mode

Use this mode first. It needs no Sarvam key, makes no network call, and spends no credits. Upload a supported file name; SpeechLens uses committed synthetic Batch output so the rest of the workflow is deterministic.

### 1. Install prerequisites

- Python 3.11 or newer.
- FFmpeg and ffprobe on `PATH` for live transcription. Fixture mode does not invoke them.

For example:

```bash
# macOS
brew install ffmpeg

# Debian/Ubuntu
sudo apt-get install ffmpeg
```

### 2. Create and install the environment

Run these commands from the repository root:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -e '.[dev]'
```

### 3. Start SpeechLens

```bash
SPEECHKIT_FIXTURE_MODE=1 \
SPEECHKIT_DATA_DIR=./data-fixture \
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. Upload an `.mp3`, `.wav`, `.m4a`, `.mp4`, `.mov`, `.mkv`, or another supported media filename. The completed view lets you rename a speaker, search for `deployment`, click a result, and export the artifact.

Check the service separately from Sarvam:

```bash
curl http://127.0.0.1:8000/health
```

Expected output:

```json
{"status":"ok","service":"speechkit","version":"0.1.0"}
```

## Live Sarvam setup

Live mode requires a Sarvam Batch STT API key and a working FFmpeg installation. Never commit the key, recordings, extracted audio, SQLite database, or downloaded provider output.

### 1. Configure local environment variables

```bash
cp .env.example .env
```

Set local values in `.env`:

```bash
SARVAM_API_KEY=your_sarvam_key
SPEECHKIT_DATA_DIR=./data
SPEECHKIT_FIXTURE_MODE=0
```

Load the file and start the service:

```bash
set -a; source .env; set +a
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```

The service binds to localhost in these examples. Do not expose it publicly without authentication, upload controls, and an operational data-retention policy: live uploads use Sarvam credits and source media is retained locally.

### 2. Use the browser demo

1. Upload a non-sensitive audio or video conversation containing clear speech.
2. Optionally supply the expected number of speakers and choose a Sarvam mode.
3. Wait for the synchronous upload request to complete.
4. Inspect speaker cards and timestamped transcript turns.
5. Rename a speaker, search, and click a result or transcript turn to seek the player.
6. Export `speechkit.v1.json` from the completed panel.

The UI offers these Sarvam Batch modes: `transcribe` (default), `translate`, `verbatim`, `translit`, and `codemix`. SpeechLens always sends `language_code="unknown"`, diarisation, and timestamps. It records the selected mode as `metadata.sarvam_mode`.

## Search guide

| UI mode | Example | What it does |
| --- | --- | --- |
| Smart | `terraform` | Weighted FTS5 token search, with close-token metadata fallback only when exact results are sparse. |
| Exact phrase | `customer managed` | FTS5 phrase query. |
| Prefix | `deploy*` | FTS5 prefix query. |
| Substring | `ploym` | Trigram FTS5 where supported; parameterised SQLite `LIKE` fallback otherwise. |
| Closest keyword | `mutatin` | RapidFuzz token similarity over keywords, entities, topics, and speaker names. |

Closest keyword is typo-tolerant matching, not semantic search. `mutatin` can match `mutating`; `genetic transformation` does not imply `mutating DNA`. No embeddings, synonym expansion, phonetic search, or LLM calls are used.

## API and safe errors

The browser uses these endpoints:

```text
GET    /health
POST   /api/assets
GET    /api/assets/{asset_id}
GET    /api/assets/{asset_id}/status
GET    /api/assets/{asset_id}/artifact
GET    /api/assets/{asset_id}/media
GET    /api/assets/{asset_id}/search?q=&mode=
PATCH  /api/assets/{asset_id}/speakers/{speaker_id}
```

All public failures use the same safe envelope. It does not contain API keys, provider headers, tracebacks, absolute local paths, signed URLs, or raw provider exceptions.

```json
{
  "error": {
    "code": "sarvam_rate_limited",
    "message": "Sarvam is rate limiting transcription requests. Retry in a few minutes.",
    "retryable": true,
    "details": {}
  }
}
```

See the generated [OpenAPI schema](docs/offcam-plugin-openapi.json) and [OffCam plugin contract](docs/offcam-plugin-contract.md) for the current executable contract.

## Tests

Default tests make no network request and require neither a Sarvam key nor FFmpeg:

```bash
.venv/bin/python -m pytest -q
```

The real Sarvam test is opt-in and may spend credits. Use only a short, non-sensitive WAV:

```bash
SARVAM_API_KEY=your_sarvam_key \
SARVAM_RUN_INTEGRATION_TESTS=1 \
SPEECHKIT_INTEGRATION_AUDIO=/path/to/non-sensitive.wav \
.venv/bin/python -m pytest -m integration
```

## Documentation

- [Setup and verification guide](docs/setup.md)
- [Implementation guide](docs/implementation-guide.md)
- [OffCam plugin contract](docs/offcam-plugin-contract.md)
- [Generated OpenAPI schema](docs/offcam-plugin-openapi.json)

## `speechkit.v1` output

```json
{
  "schema_version": "speechkit.v1",
  "provider": "sarvam",
  "model": "saaras:v3",
  "speakers": [{"speaker_id": "speaker_0", "display_name": "Speaker 0"}],
  "segments": [{"speaker_id": "speaker_0", "start_seconds": 0.01, "end_seconds": 2.5, "text": "Hello"}]
}
```

An OffCam integration should consume the artifact and public HTTP contract, rather than import the standalone UI or Sarvam SDK.
