import pytest
from pathlib import Path

from speechkit.exceptions import ProviderError
from speechkit.sarvam_provider import SarvamProvider


class ApiError(Exception):
    def __init__(self, status_code): self.status_code = status_code


@pytest.mark.parametrize("status", [429, 500, 503])
def test_retries_transient_create_job_failures(monkeypatch, status):
    attempts = {"count": 0}
    provider = SarvamProvider("key", sleep=lambda _: None, random_value=lambda: 0)

    def create(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ApiError(status)
        return object()

    monkeypatch.setattr(provider, "_create_job", create)
    assert provider._with_retry(lambda: provider._create_job()) is not None
    assert attempts["count"] == 3


@pytest.mark.parametrize("status", [403, 413, 422])
def test_does_not_retry_non_transient_failures(status):
    provider = SarvamProvider("key", sleep=lambda _: None)
    with pytest.raises(ProviderError):
        provider._with_retry(lambda: (_ for _ in ()).throw(ApiError(status)))


def test_invalid_downloaded_transcript_json_is_a_provider_error(monkeypatch, tmp_path):
    class Job:
        job_id = "job"
        def upload_files(self, **_kwargs): pass
        def start(self): pass
        def wait_until_complete(self, **_kwargs): return self
        def get_file_results(self): return {"successful": [{}], "failed": []}
        def download_outputs(self, output_dir): Path(output_dir, "output.json").write_text("not json")

    provider = SarvamProvider("key", sleep=lambda _: None)
    monkeypatch.setattr(provider, "_create_job", lambda **_kwargs: Job())
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"wav")
    with pytest.raises(ProviderError, match="invalid JSON"):
        provider.transcribe_batch(audio)


def test_malformed_batch_file_results_is_a_provider_error(monkeypatch, tmp_path):
    class Job:
        job_id = "job"
        def upload_files(self, **_kwargs): pass
        def start(self): pass
        def wait_until_complete(self, **_kwargs): return self
        def get_file_results(self): return []

    provider = SarvamProvider("key", sleep=lambda _: None)
    monkeypatch.setattr(provider, "_create_job", lambda **_kwargs: Job())
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"wav")
    with pytest.raises(ProviderError, match="invalid file results"):
        provider.transcribe_batch(audio)
