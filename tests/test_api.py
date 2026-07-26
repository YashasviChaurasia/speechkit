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
