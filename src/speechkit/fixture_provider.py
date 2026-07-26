from __future__ import annotations

import json
from pathlib import Path


class FixtureProvider:
    """Deterministic local Batch-STT substitute for integration tests."""

    def transcribe_batch(self, _audio_path: Path, *, num_speakers: int | None = None, mode: str = "transcribe") -> tuple[dict, str, list[dict]]:
        output = json.loads((Path(__file__).parent / "fixtures" / "offcam_batch_output.json").read_text())
        return output, "fixture-job", []
