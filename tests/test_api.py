import importlib
import sys

from fastapi.testclient import TestClient


def test_search_endpoint_rejects_unknown_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    monkeypatch.setenv("SPEECHKIT_DATA_DIR", str(tmp_path))
    sys.modules.pop("app", None)
    app = importlib.import_module("app")
    response = TestClient(app.app).get("/api/assets/missing/search?q=test&mode=vector")
    assert response.status_code == 422


def test_search_endpoint_accepts_closest_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    monkeypatch.setenv("SPEECHKIT_DATA_DIR", str(tmp_path))
    sys.modules.pop("app", None)
    app = importlib.import_module("app")
    response = TestClient(app.app).get("/api/assets/missing/search?q=spidr&mode=closest")
    assert response.status_code == 200
    assert response.json()["mode"] == "closest"


def test_upload_passes_documented_sarvam_mode_to_processing(monkeypatch, tmp_path):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    monkeypatch.setenv("SPEECHKIT_DATA_DIR", str(tmp_path))
    sys.modules.pop("app", None)
    app = importlib.import_module("app")
    captured = {}

    def process(_filename, _path, _speakers, mode, _provider):
        captured["mode"] = mode
        return "asset"

    monkeypatch.setattr(app.service, "process", process)
    monkeypatch.setattr(app.credentials, "get", lambda: "test-key")
    response = TestClient(app.app).post("/api/assets", data={"mode": "translit"}, files={"file": ("recording.wav", b"RIFF", "audio/wav")})
    assert response.status_code == 200
    assert captured["mode"] == "translit"


def test_upload_rejects_unknown_sarvam_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    monkeypatch.setenv("SPEECHKIT_DATA_DIR", str(tmp_path))
    sys.modules.pop("app", None)
    app = importlib.import_module("app")
    response = TestClient(app.app).post("/api/assets", data={"mode": "semantic"}, files={"file": ("recording.wav", b"RIFF", "audio/wav")})
    assert response.status_code == 422
