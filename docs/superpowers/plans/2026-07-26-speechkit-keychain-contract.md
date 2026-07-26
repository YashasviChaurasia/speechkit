# SpeechKit Keychain Credential Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store the Sarvam API key in the operating-system credential store and expose safe demo-only provider-configuration endpoints.

**Architecture:** A small `credentials.py` module owns the `keyring` calls and translates keychain failures into a domain exception. FastAPI reads the stored value per live analysis request, while fixture mode remains credential-free. The API returns only provider/configured state and keeps the key out of JSON, SQLite, logs, fixtures, and public errors.

**Tech Stack:** Python 3.11, FastAPI, `keyring==25.7.0`, pytest, existing Sarvam SDK.

## Global Constraints

- Use the operating-system credential store only for Sarvam API-key persistence.
- Do not read or write `SARVAM_API_KEY`, `.env`, SQLite, JSON, browser storage, or an encrypted local secret file.
- Keep credential endpoints unauthenticated only for this localhost/demo scope; document that they require an OffCam backend proxy or network isolation before production.
- Responses and errors never contain a key, provider headers, raw exception, or submitted request body.
- Keep offline fixture uploads deterministic without any configured key.
- Do not modify the OffCam repository; document the proxy/UI contract in SpeechKit docs.

---

### Task 1: Add a testable keychain boundary

**Files:**
- Create: `src/speechkit/credentials.py`
- Create: `tests/test_credentials.py`
- Modify: `src/speechkit/exceptions.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces `CredentialStore.get() -> str | None`, `CredentialStore.save(api_key: str) -> None`, and `CredentialStore.remove() -> None`.
- Produces `CredentialStoreError`, which app maps to a safe public error.

- [ ] **Step 1: Write failing keychain-boundary tests**

```python
def test_store_reads_saves_and_removes_only_the_sarvam_entry(monkeypatch):
    calls = []
    monkeypatch.setattr("speechkit.credentials.keyring.get_password", lambda service, account: calls.append(("get", service, account)) or "stored")
    monkeypatch.setattr("speechkit.credentials.keyring.set_password", lambda service, account, value: calls.append(("set", service, account, value)))
    monkeypatch.setattr("speechkit.credentials.keyring.delete_password", lambda service, account: calls.append(("delete", service, account)))
    store = CredentialStore()
    assert store.get() == "stored"
    store.save("new-key")
    store.remove()
    assert calls == [("get", "speechkit", "sarvam"), ("set", "speechkit", "sarvam", "new-key"), ("delete", "speechkit", "sarvam")]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_credentials.py`

Expected: FAIL because `speechkit.credentials` does not exist.

- [ ] **Step 3: Add the minimal production boundary**

```python
class CredentialStore:
    service_name = "speechkit"
    account_name = "sarvam"

    def get(self) -> str | None:
        return keyring.get_password(self.service_name, self.account_name)
```

Wrap `keyring.errors.KeyringError` and unexpected backend exceptions in `CredentialStoreError`; treat a missing credential during delete as a successful already-removed state. Pin `keyring==25.7.0` in project dependencies.

- [ ] **Step 4: Run the keychain-boundary tests to verify they pass**

Run: `.venv/bin/python -m pytest -q tests/test_credentials.py`

Expected: PASS.

- [ ] **Step 5: Commit the keychain boundary**

```bash
git add pyproject.toml src/speechkit/credentials.py src/speechkit/exceptions.py tests/test_credentials.py
git commit -m "feat: store Sarvam credentials in keychain"
```

### Task 2: Add safe provider configuration endpoints

**Files:**
- Modify: `app.py`
- Modify: `tests/test_offcam_contract.py`

**Interfaces:**
- Consumes `CredentialStore` from Task 1.
- Produces `GET`, `PUT`, and `DELETE /api/provider/config` with `{"provider":"sarvam","configured":bool}` responses.

- [ ] **Step 1: Write failing HTTP-contract tests**

```python
def test_provider_config_never_returns_the_submitted_key(monkeypatch, tmp_path):
    application = fixture_app(monkeypatch, tmp_path)
    fake = FakeCredentials()
    monkeypatch.setattr(application, "credentials", fake)
    client = TestClient(application.app)
    assert client.get("/api/provider/config").json() == {"provider": "sarvam", "configured": False}
    response = client.put("/api/provider/config", json={"api_key": "secret-value"})
    assert response.json() == {"provider": "sarvam", "configured": True}
    assert "secret-value" not in response.text
    assert client.delete("/api/provider/config").json() == {"provider": "sarvam", "configured": False}
```

- [ ] **Step 2: Run the endpoint test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_offcam_contract.py::test_provider_config_never_returns_the_submitted_key`

Expected: FAIL with `404` because the provider config path does not exist.

- [ ] **Step 3: Add typed config routes and safe keychain failure mapping**

Add a `ProviderConfiguration` response model and `ProviderKey` request model with a non-blank `api_key`. Map `CredentialStoreError` to `500 credential_store_unavailable` and ensure every success body contains only `provider` and `configured`.

- [ ] **Step 4: Run the endpoint test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_offcam_contract.py::test_provider_config_never_returns_the_submitted_key`

Expected: PASS.

- [ ] **Step 5: Commit the public contract**

```bash
git add app.py tests/test_offcam_contract.py
git commit -m "feat: add SpeechKit provider config contract"
```

### Task 3: Resolve credentials per live analysis and document the contract

**Files:**
- Modify: `src/speechkit/config.py`
- Modify: `src/speechkit/service.py`
- Modify: `app.py`
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `docs/offcam-plugin-contract.md`
- Modify: `docs/offcam-plugin-openapi.json`
- Modify: `tests/test_offcam_contract.py`

**Interfaces:**
- Consumes `CredentialStore.get()` and the existing `SarvamProvider(api_key, ...)` constructor.
- Produces `sarvam_not_configured` for live upload without a stored key and preserves `sarvam_authentication` for a rejected stored key.

- [ ] **Step 1: Write failing live-analysis credential tests**

```python
def test_live_upload_requires_a_stored_sarvam_key(monkeypatch, tmp_path):
    application = live_app(monkeypatch, tmp_path)
    monkeypatch.setattr(application, "credentials", EmptyCredentials())
    response = TestClient(application.app).post("/api/assets", files={"file": ("recording.wav", b"audio", "audio/wav")})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "sarvam_not_configured"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_offcam_contract.py::test_live_upload_requires_a_stored_sarvam_key`

Expected: FAIL because live startup currently requires `SARVAM_API_KEY` and constructs a provider at import time.

- [ ] **Step 3: Resolve a provider at upload time**

Remove API-key handling from `Settings`. Permit live startup with no configured key. Add an optional provider parameter to `SpeechService.process`; in live upload, obtain the key from `credentials`, return `sarvam_not_configured` when absent, and pass a new `SarvamProvider` to `process`. Fixture mode continues to use `FixtureProvider` and does not read credentials.

- [ ] **Step 4: Run the live-analysis credential test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_offcam_contract.py::test_live_upload_requires_a_stored_sarvam_key`

Expected: PASS.

- [ ] **Step 5: Generate contract documentation and verify the full suite**

Run:

```bash
SPEECHKIT_FIXTURE_MODE=1 SPEECHKIT_DATA_DIR=/tmp/speechkit-openapi \
  .venv/bin/uvicorn app:app --host 127.0.0.1 --port 8013
curl --fail --silent http://127.0.0.1:8013/openapi.json
.venv/bin/python -m pytest -q
```

Document the three endpoints, keychain ownership, no-secret response rule, demo-only privacy boundary, OffCam proxy UI requirements, and configuration-related errors. Regenerate OpenAPI from the running app rather than hand-writing it.

- [ ] **Step 6: Commit the runtime and docs**

```bash
git add app.py src/speechkit/config.py src/speechkit/service.py .env.example README.md docs/offcam-plugin-contract.md docs/offcam-plugin-openapi.json tests/test_offcam_contract.py
git commit -m "feat: use stored Sarvam credentials for analysis"
```

## Plan self-review

- **Spec coverage:** Task 1 provides OS keychain storage and tests. Task 2 provides safe configuration endpoints. Task 3 removes environment-key ownership, resolves live credentials per upload, preserves fixture mode, and updates all required contract documentation.
- **Scope:** No OffCam source file is touched because this repository contains SpeechKit only. The OffCam password UI and server-side proxy behavior are documented as its integration contract.
- **Consistency:** `CredentialStore`, `CredentialStoreError`, `ProviderConfiguration`, and `sarvam_not_configured` are defined before their later use. Each functional change starts with a failing pytest assertion.
