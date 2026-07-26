# SpeechLens demo setup

## Prerequisites

- Python 3.11 or newer
- FFmpeg and ffprobe available on your `PATH`
- A Sarvam API key with Batch STT credits for live transcription, stored through the provider configuration contract

## Install

```bash
cd speechlens
cp .env.example .env
```

Edit `.env` and set only non-secret runtime values:

```bash
SPEECHKIT_DATA_DIR=./data
SPEECHKIT_FIXTURE_MODE=0
```

Then install dependencies:

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -e '.[dev]'
```

## Start the demo

```bash
set -a; source .env; set +a
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in a browser on the same machine. This binds only to localhost; do not expose the application publicly without adding access control because uploads consume Sarvam credits.

SpeechKit does not read `SARVAM_API_KEY` from `.env`. Its OffCam backend proxy configures the operating-system credential store through `GET`, `PUT`, and `DELETE /api/provider/config`. The standalone browser UI has no key form. A live upload with no stored key returns the safe `sarvam_not_configured` error.

## Run without Sarvam credentials

Fixture mode is useful for UI reviews and OffCam contract tests. It requires no key, makes no network request, and uses a committed synthetic Batch response instead of real transcription:

```bash
SPEECHKIT_FIXTURE_MODE=1 \
SPEECHKIT_DATA_DIR=./data-fixture \
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```

Upload any supported media filename to exercise upload, status, artifact, search, rename, playback, and export. Do not treat fixture output as a transcription result.

## Verify the flow

1. Upload a non-sensitive audio or video conversation.
2. Wait for extraction, Batch STT, diarisation, and indexing to finish.
3. Rename a speaker and search that new name.
4. Try Smart, Exact phrase, Prefix, Substring, and Closest keyword search. Closest keyword uses RapidFuzz against indexed keywords, entities, topics, and speaker names for typo-tolerant token matching (for example, `mutatin` → `mutating`). It is not semantic or conceptual search.
5. Click a result or transcript turn to seek the media player.
6. Export the `speechkit.v1.json` artifact.

## Tests

```bash
.venv/bin/python -m pytest -q
```

Run the real Sarvam test only when you deliberately want to use credits:

```bash
SARVAM_RUN_INTEGRATION_TESTS=1 \
SARVAM_API_KEY=your_sarvam_key \
SPEECHKIT_INTEGRATION_AUDIO=/absolute/path/to/non-sensitive.wav \
.venv/bin/python -m pytest -m integration
```

`data/`, `.env`, generated audio, and downloaded Sarvam results are ignored by Git.
