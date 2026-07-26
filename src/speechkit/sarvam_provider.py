from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Callable

from sarvamai import SarvamAI

from .exceptions import ProviderError


class SarvamProvider:
    def __init__(self, api_key: str, *, timeout: float = 60.0, poll_interval: int = 5, batch_timeout: int = 1800, sleep: Callable[[float], None] = time.sleep, random_value: Callable[[], float] = random.random):
        self.client = SarvamAI(api_subscription_key=api_key, timeout=timeout)
        self.poll_interval, self.batch_timeout, self.sleep, self.random_value = poll_interval, batch_timeout, sleep, random_value

    def _retryable(self, error: Exception) -> bool:
        return getattr(error, "status_code", None) in {408, 429, 500, 503} or isinstance(error, ConnectionError)

    def _with_retry(self, call):
        for attempt in range(5):
            try: return call()
            except Exception as error:
                if not self._retryable(error) or attempt == 4: raise ProviderError(f"Sarvam request failed: {error}") from error
                self.sleep(min(1 * 2 ** attempt, 30) + self.random_value())

    def _create_job(self, **kwargs):
        return self.client.speech_to_text_job.create_job(**kwargs)

    def transcribe_batch(self, audio_path: Path, *, num_speakers: int | None = None) -> tuple[dict, str, list[dict]]:
        kwargs = {"model": "saaras:v3", "mode": "transcribe", "language_code": "unknown", "with_diarization": True, "with_timestamps": True}
        if num_speakers: kwargs["num_speakers"] = num_speakers
        job = self._with_retry(lambda: self._create_job(**kwargs))
        self._with_retry(lambda: job.upload_files(file_paths=[str(audio_path)]))
        self._with_retry(job.start)
        try:
            status = job.wait_until_complete(poll_interval=self.poll_interval, timeout=self.batch_timeout)
            files = job.get_file_results()
        except Exception as error:
            raise ProviderError("Sarvam batch job could not be completed.") from error
        if not isinstance(files, dict):
            raise ProviderError("Sarvam returned invalid file results.")
        successful, failed = files.get("successful", []), files.get("failed", [])
        if not isinstance(successful, list) or not isinstance(failed, list):
            raise ProviderError("Sarvam returned invalid file results.")
        if not successful: raise ProviderError(f"Batch job completed without successful files: {failed}")
        output_dir = audio_path.parent / "sarvam-output"; output_dir.mkdir(exist_ok=True)
        try:
            job.download_outputs(output_dir=str(output_dir))
        except Exception as error:
            raise ProviderError("Sarvam could not download the transcript artifact.") from error
        output_file = next(output_dir.glob("*.json"), None)
        if not output_file: raise ProviderError("Sarvam did not download a JSON transcript artifact")
        import json
        try:
            output = json.loads(output_file.read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise ProviderError("Sarvam downloaded invalid JSON transcript data.") from error
        if not isinstance(output, dict):
            raise ProviderError("Sarvam downloaded an invalid transcript payload.")
        return output, str(getattr(status, "job_id", getattr(job, "job_id", "unknown"))), failed
