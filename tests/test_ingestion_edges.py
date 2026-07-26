import importlib
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from speechkit.exceptions import MediaError, ProviderError
from speechkit.media import MediaInfo, inspect_media
from speechkit.normalize import normalize_batch_output
from speechkit.service import SpeechService
from speechkit.storage import Storage


def test_upload_rejects_empty_or_unsupported_files_before_processing(monkeypatch, tmp_path):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    monkeypatch.setenv("SPEECHKIT_DATA_DIR", str(tmp_path))
    sys.modules.pop("app", None)
    application = importlib.import_module("app")
    monkeypatch.setattr(application.service, "process", lambda *_: pytest.fail("invalid upload reached processing"))
    client = TestClient(application.app)
    assert client.post("/api/assets", files={"file": ("empty.wav", b"", "audio/wav")}).status_code == 400
    assert client.post("/api/assets", files={"file": ("notes.txt", b"not media", "text/plain")}).status_code == 415


def test_upload_returns_actionable_sarvam_response_error(monkeypatch, tmp_path):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    monkeypatch.setenv("SPEECHKIT_DATA_DIR", str(tmp_path))
    sys.modules.pop("app", None)
    application = importlib.import_module("app")

    def malformed_response(*_args):
        raise ProviderError("Sarvam downloaded invalid JSON transcript data.")

    monkeypatch.setattr(application.service, "process", malformed_response)
    response = TestClient(application.app).post("/api/assets", files={"file": ("recording.wav", b"RIFF", "audio/wav")})
    assert response.status_code == 502
    assert response.json()["error"] == {"code": "provider_response_invalid", "message": "Sarvam returned unusable transcription data. Retry the recording later.", "retryable": True, "details": {}}


def test_upload_rejects_invalid_expected_speaker_count(monkeypatch, tmp_path):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    monkeypatch.setenv("SPEECHKIT_DATA_DIR", str(tmp_path))
    sys.modules.pop("app", None)
    application = importlib.import_module("app")
    monkeypatch.setattr(application.service, "process", lambda *_: pytest.fail("invalid speaker count reached processing"))
    response = TestClient(application.app).post("/api/assets", data={"num_speakers": "0"}, files={"file": ("recording.wav", b"RIFF", "audio/wav")})
    assert response.status_code == 422


def test_inspect_media_rejects_nonpositive_or_missing_duration(monkeypatch, tmp_path):
    media = tmp_path / "recording.wav"
    media.write_bytes(b"audio")
    monkeypatch.setattr("speechkit.media.subprocess.run", lambda *_, **__: subprocess.CompletedProcess([], 0, '{"format":{"duration":"0","format_name":"wav"},"streams":[{"codec_type":"audio"}]}', ""))
    with pytest.raises(MediaError, match="duration"):
        inspect_media(media)


def test_inspect_media_rejects_video_without_an_audio_track(monkeypatch, tmp_path):
    media = tmp_path / "video.mp4"
    media.write_bytes(b"video")
    monkeypatch.setattr("speechkit.media.subprocess.run", lambda *_, **__: subprocess.CompletedProcess([], 0, '{"format":{"duration":"5","format_name":"mp4"},"streams":[{"codec_type":"video"}]}', ""))
    with pytest.raises(MediaError, match="no audio track"):
        inspect_media(media)


def test_normalize_ignores_blank_or_invalid_diarised_entries():
    artifact = normalize_batch_output(
        asset_id="asset", filename="recording.wav", duration_seconds=10,
        output={"diarized_transcript": {"entries": [
            {"transcript": "", "speaker_id": "0", "start_time_seconds": 0, "end_time_seconds": 1},
            {"transcript": "Broken", "speaker_id": "0", "start_time_seconds": 4, "end_time_seconds": 2},
            {"transcript": "Valid speech", "speaker_id": "1", "start_time_seconds": 2, "end_time_seconds": 4},
        ]}},
        job_id="job", estimated_cost_inr=0.1,
    )
    assert [segment.text for segment in artifact.segments] == ["Valid speech"]


def test_normalize_rejects_malformed_provider_payload():
    with pytest.raises(ProviderError, match="invalid transcript payload"):
        normalize_batch_output(asset_id="asset", filename="recording.wav", duration_seconds=1, output=[], job_id="job", estimated_cost_inr=0.1)


class EmptyTranscriptProvider:
    def transcribe_batch(self, *_args, **_kwargs):
        return {"diarized_transcript": {"entries": []}}, "job-empty", []


class MalformedTranscriptProvider:
    def transcribe_batch(self, *_args, **_kwargs):
        return [], "job-malformed", []


def test_service_marks_speechless_recording_failed(monkeypatch, tmp_path):
    store = Storage(tmp_path / "speechlens.sqlite")
    service = SpeechService(store, EmptyTranscriptProvider(), tmp_path)
    upload = tmp_path / "upload.wav"
    upload.write_bytes(b"audio")
    monkeypatch.setattr("speechkit.service.inspect_media", lambda *_: MediaInfo(3, "wav"))

    def extract(_source: Path, target: Path, _ffmpeg: str) -> Path:
        target.write_bytes(b"wav")
        return target

    monkeypatch.setattr("speechkit.service.extract_audio", extract)
    with pytest.raises(ProviderError, match="clear spoken dialogue"):
        service.process("upload.wav", upload)
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT status FROM assets").fetchone()[0] == "failed"


def test_service_marks_malformed_provider_response_failed(monkeypatch, tmp_path):
    store = Storage(tmp_path / "speechlens.sqlite")
    service = SpeechService(store, MalformedTranscriptProvider(), tmp_path)
    upload = tmp_path / "upload.wav"
    upload.write_bytes(b"audio")
    monkeypatch.setattr("speechkit.service.inspect_media", lambda *_: MediaInfo(3, "wav"))
    monkeypatch.setattr("speechkit.service.extract_audio", lambda _source, target, _ffmpeg: target)
    with pytest.raises(ProviderError, match="invalid transcript payload"):
        service.process("upload.wav", upload)
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT status FROM assets").fetchone()[0] == "failed"
