import os
from pathlib import Path

import pytest

from speechkit.sarvam_provider import SarvamProvider


@pytest.mark.integration
def test_real_sarvam_batch_response_has_transcript():
    if os.getenv("SARVAM_RUN_INTEGRATION_TESTS") != "1":
        pytest.skip("set SARVAM_RUN_INTEGRATION_TESTS=1 to spend Sarvam credits")
    audio = os.getenv("SPEECHKIT_INTEGRATION_AUDIO")
    if not audio:
        pytest.skip("set SPEECHKIT_INTEGRATION_AUDIO to a short non-sensitive WAV")
    output, job_id, _ = SarvamProvider(os.environ["SARVAM_API_KEY"]).transcribe_batch(Path(audio))
    assert job_id
    assert output.get("transcript")
