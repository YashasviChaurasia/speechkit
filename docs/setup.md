# SpeechLens demo setup

## Prerequisites

- Python 3.11 or newer
- FFmpeg and ffprobe available on your `PATH`
- A Sarvam API key with Batch STT credits

## Install

```bash
cd speechlens
cp .env.example .env
```

Edit `.env` and set only your local values:

```bash
SARVAM_API_KEY=your_key_here
SPEECHKIT_DATA_DIR=./data
SARVAM_RUN_INTEGRATION_TESTS=0
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
SPEECHKIT_INTEGRATION_AUDIO=/absolute/path/to/non-sensitive.wav \
.venv/bin/python -m pytest -m integration
```

`data/`, `.env`, generated audio, and downloaded Sarvam results are ignored by Git.
