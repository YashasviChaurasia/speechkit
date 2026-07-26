import importlib
import json
import sys

import pytest
from fastapi.testclient import TestClient

from speechkit.exceptions import MediaError, ProviderError
from speechkit.models import SpeechArtifact, SpeechSegment, SpeakerProfile
from speechkit.storage import Storage


def fixture_app(monkeypatch, tmp_path):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    monkeypatch.setenv("SPEECHKIT_FIXTURE_MODE", "1")
    monkeypatch.setenv("SPEECHKIT_DATA_DIR", str(tmp_path))
    sys.modules.pop("app", None)
    return importlib.import_module("app")


def test_fixture_mode_starts_without_a_sarvam_key_and_has_typed_health(monkeypatch, tmp_path):
    application = fixture_app(monkeypatch, tmp_path)
    response = TestClient(application.app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "speechkit", "version": "0.1.0"}


def test_fixture_mode_is_deterministic_for_analyse_status_artifact_search_and_rename(monkeypatch, tmp_path):
    application = fixture_app(monkeypatch, tmp_path)
    client = TestClient(application.app)
    upload = client.post("/api/assets", data={"mode": "translit"}, files={"file": ("meeting.mp4", b"fixture media", "video/mp4")})
    assert upload.status_code == 200
    asset_id = upload.json()["asset_id"]
    assert client.get(f"/api/assets/{asset_id}/status").json()["status"] == "complete"
    artifact = client.get(f"/api/assets/{asset_id}/artifact").json()
    assert artifact["metadata"]["sarvam_mode"] == "translit"
    assert "media_path" not in artifact["metadata"]
    assert client.get(f"/api/assets/{asset_id}/search?q=deployment&mode=smart").json()["results"]
    speaker_id = artifact["speakers"][0]["speaker_id"]
    assert client.patch(f"/api/assets/{asset_id}/speakers/{speaker_id}", json={"display_name": "Alex"}).status_code == 200
    assert client.get(f"/api/assets/{asset_id}/artifact").json()["speakers"][0]["display_name"] == "Alex"


def test_public_storage_output_redacts_paths_and_persisted_errors(tmp_path):
    store = Storage(tmp_path / "speechlens.sqlite")
    store.create_asset("asset", "meeting.wav")
    artifact = SpeechArtifact("speechkit.v1", "asset", "meeting.wav", 2, "sarvam", "saaras:v3", None, [SpeakerProfile("speaker_0", "Speaker 0", 1, 100, 1, 1, 1, 1, 0)], [SpeechSegment("segment", "asset", "speaker_0", "Speaker 0", "Hello", 0, 1)], {"media_path": "/private/recording.wav"})
    store.save_artifact(artifact)
    assert "media_path" not in store.get_artifact("asset")["metadata"]
    store.set_status("asset", "failed", "headers: secret /private/recording.wav")
    assert "/private/" not in json.dumps(store.get_asset("asset"))


def test_public_errors_have_a_stable_safe_envelope(monkeypatch, tmp_path):
    application = fixture_app(monkeypatch, tmp_path)
    client = TestClient(application.app)
    missing = client.get("/api/assets/missing")
    assert missing.status_code == 404
    assert missing.json() == {"error": {"code": "asset_not_found", "message": "Asset not found.", "retryable": False, "details": {}}}

    monkeypatch.setattr(application.service, "process", lambda *_: (_ for _ in ()).throw(MediaError("This video has no audio track.")))
    no_audio = client.post("/api/assets", files={"file": ("video.mp4", b"video", "video/mp4")})
    assert no_audio.json()["error"]["code"] == "media_no_audio"
    assert no_audio.json()["error"]["retryable"] is False

    auth = ProviderError("headers: secret")
    auth.status_code = 403
    monkeypatch.setattr(application.service, "process", lambda *_: (_ for _ in ()).throw(auth))
    response = client.post("/api/assets", files={"file": ("audio.wav", b"audio", "audio/wav")})
    assert response.json()["error"] == {"code": "sarvam_authentication", "message": "Sarvam authentication failed. Check the backend API key configuration.", "retryable": False, "details": {}}


@pytest.mark.parametrize(("status_code", "message", "code", "status"), [
    (429, "secret headers", "sarvam_rate_limited", 503),
    (504, "private timeout detail", "provider_timeout", 504),
])
def test_transient_provider_errors_are_safe_and_retryable(monkeypatch, tmp_path, status_code, message, code, status):
    application = fixture_app(monkeypatch, tmp_path)
    error = ProviderError(message, status_code)
    monkeypatch.setattr(application.service, "process", lambda *_: (_ for _ in ()).throw(error))
    response = TestClient(application.app).post("/api/assets", files={"file": ("audio.wav", b"audio", "audio/wav")})
    assert response.status_code == status
    assert response.json()["error"] == {"code": code, "message": response.json()["error"]["message"], "retryable": True, "details": {}}
    assert message not in response.text
