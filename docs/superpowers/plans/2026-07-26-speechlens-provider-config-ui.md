# SpeechLens Provider Configuration UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a standalone browser reference for configuring the existing SpeechKit Sarvam credential.

**Architecture:** Static markup presents a small credential card ahead of the upload form. Browser-native JavaScript calls only the existing same-origin provider configuration endpoints and clears the input after use. CSS uses the current workspace visual system.

**Tech Stack:** Plain HTML, CSS, browser-native JavaScript, pytest.

## Global Constraints

- Do not change backend endpoints or artifact schemas.
- Never retain, render, log, or export an API key in browser state.
- Analyse stays disabled until `GET /api/provider/config` reports configured.

---

### Task 1: Credential configuration UI

**Files:**
- Modify: `static/index.html`
- Modify: `static/styles.css`
- Modify: `static/app.js`
- Test: `tests/test_ui_shell.py`

**Interfaces:**
- Consumes: `GET|PUT|DELETE /api/provider/config`.
- Produces: a configuration card that controls `#analyse` disabled state.

- [x] **Step 1: Write the failing static UI test**

```python
def test_ui_exposes_provider_configuration_without_storing_keys():
    html = Path("static/index.html").read_text()
    script = Path("static/app.js").read_text()
    assert 'id="provider-config"' in html
    assert 'type="password"' in html
    assert '"/api/provider/config"' in script
    assert "apiKey.value = \"\"" in script
```

- [x] **Step 2: Run the focused test and verify it fails**

Run: `.venv/bin/python -m pytest tests/test_ui_shell.py -q`
Expected: FAIL because the configuration controls do not exist.

- [x] **Step 3: Add the minimal configuration card and client flow**

```javascript
async function refreshProviderConfig() {
  const response = await fetch("/api/provider/config");
  const data = await response.json();
  setConfigured(Boolean(data.configured));
}
```

Use PUT for saving, DELETE for removal, clear the password input in `finally`, and keep the input value out of all other state.

- [x] **Step 4: Run the focused test and full suite**

Run: `.venv/bin/python -m pytest tests/test_ui_shell.py -q && .venv/bin/python -m pytest -q`
Expected: all tests pass.

- [x] **Step 5: Commit**

```bash
git add static/index.html static/styles.css static/app.js tests/test_ui_shell.py docs/superpowers/plans/2026-07-26-speechlens-provider-config-ui.md
git commit -m "feat: add SpeechLens provider configuration UI"
```
