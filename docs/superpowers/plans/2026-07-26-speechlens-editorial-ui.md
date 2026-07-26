# SpeechLens Editorial Workspace UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernise the existing SpeechLens single-page UI into an elegant editorial analysis workspace without changing its API, data flow, or plain-browser technology stack.

**Architecture:** Keep `static/index.html` as the semantic page skeleton, `static/styles.css` as the complete visual system, and `static/app.js` as the existing API/rendering boundary. Add only a light in-page rail navigation state; existing element IDs and endpoint calls remain stable.

**Tech Stack:** Plain HTML, CSS, browser-native JavaScript, FastAPI static file mount, pytest.

## Global Constraints

- Keep FastAPI endpoints, request payloads, `speechkit.v1`, and Sarvam integration unchanged.
- Keep the existing one-page workflow: upload, render, rename, search, seek, transcript, export.
- Use no React, external UI library, external font, backend change, or new dependency.
- Use the design tokens from `docs/superpowers/specs/2026-07-26-speechlens-editorial-ui-design.md`.
- Preserve keyboard-accessible buttons, labels, visible focus, and reduced-motion support.
- Render public error-envelope messages through `error.message`, never raw `detail` alone.

---

### Task 1: Lock the static workspace contract

**Files:**
- Create: `tests/test_ui_shell.py`
- Modify: `static/index.html`

**Interfaces:**
- Consumes: existing JavaScript IDs `upload`, `status`, `result`, `media`, `filename`, `facts`, `speaker-cards`, `query`, `mode`, `search`, `search-meta`, `results`, `segments`, `raw`, and `export`.
- Produces: anchor targets `upload-panel`, `overview`, `speakers`, `search-panel`, `transcript`, and `artifact`; rail links that target each ID.

- [x] **Step 1: Write the failing static-shell test**

```python
from pathlib import Path


def test_editorial_shell_has_navigation_and_stable_render_targets():
    html = Path("static/index.html").read_text()
    for target in ("upload-panel", "overview", "speakers", "search-panel", "transcript", "artifact"):
        assert f'id="{target}"' in html
        assert f'href="#{target}"' in html
    for element_id in ("upload", "status", "result", "media", "filename", "facts", "speaker-cards", "query", "mode", "search", "results", "segments", "raw", "export"):
        assert f'id="{element_id}"' in html
```

- [x] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_ui_shell.py::test_editorial_shell_has_navigation_and_stable_render_targets`

Expected: FAIL because the current shell has no `upload-panel` or rail anchors.

- [x] **Step 3: Rebuild `static/index.html` as the editorial shell**

Use this structural outline while retaining all existing form names and render IDs:

```html
<aside class="rail" aria-label="SpeechLens sections">
  <a class="rail-brand" href="#upload-panel">SpeechLens</a>
  <nav>
    <a href="#upload-panel"><span>01</span> Upload</a>
    <a href="#overview"><span>02</span> Overview</a>
    <a href="#speakers"><span>03</span> Speakers</a>
    <a href="#search-panel"><span>04</span> Search</a>
    <a href="#transcript"><span>05</span> Transcript</a>
    <a href="#artifact"><span>06</span> Artifact</a>
  </nav>
</aside>
<main class="workspace">…existing controls and targets…</main>
```

Place the upload form in `#upload-panel`; place the completed player/facts in `#overview`; give the raw artifact `<details>` container `id="artifact"`. Keep `#result` hidden until `render()` runs.

- [x] **Step 4: Run the static-shell test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_ui_shell.py::test_editorial_shell_has_navigation_and_stable_render_targets`

Expected: PASS.

- [x] **Step 5: Commit the shell contract**

```bash
git add static/index.html tests/test_ui_shell.py
git commit -m "feat: add SpeechLens workspace shell"
```

### Task 2: Apply the responsive editorial visual system

**Files:**
- Modify: `static/styles.css`
- Modify: `tests/test_ui_shell.py`

**Interfaces:**
- Consumes: rail and section classes from Task 1, plus existing generated classes `speaker-card`, `result`, `segment`, `tags`, `entities`, `close-match`, and `empty`.
- Produces: desktop two-column workspace, compact mobile rail, visible focus styles, and reduced-motion support.

- [x] **Step 1: Add the failing visual-system assertions**

```python
def test_editorial_styles_define_workspace_accessibility_and_mobile_layout():
    css = Path("static/styles.css").read_text()
    for selector in (".rail", ".workspace", ".section-marker", ":focus-visible", "prefers-reduced-motion", "@media(max-width:820px)"):
        assert selector in css
```

- [x] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_ui_shell.py::test_editorial_styles_define_workspace_accessibility_and_mobile_layout`

Expected: FAIL because the current CSS lacks the rail and reduced-motion rules.

- [x] **Step 3: Replace `static/styles.css` with the scoped visual system**

Define the documented paper, surface, ink, quiet, rule, cobalt, and warm-marker CSS variables. Use a fixed `260px` rail on desktop, a max-width canvas, border-led white cards, and compact monospace labels. Add:

```css
:focus-visible { outline: 3px solid var(--cobalt); outline-offset: 3px; }
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto; transition: none !important; } }
@media (max-width: 820px) { .app-shell { display: block; } .rail { position: sticky; top: 0; overflow-x: auto; } }
```

Ensure result cards, transcript buttons, input controls, speaker cards, raw artifact, and status styles remain readable and interactive.

- [x] **Step 4: Run the visual-system test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_ui_shell.py::test_editorial_styles_define_workspace_accessibility_and_mobile_layout`

Expected: PASS.

- [x] **Step 5: Commit the visual system**

```bash
git add static/styles.css tests/test_ui_shell.py
git commit -m "feat: style SpeechLens editorial workspace"
```

### Task 3: Make rendering match the shell and safe error contract

**Files:**
- Modify: `static/app.js`
- Modify: `tests/test_ui_shell.py`

**Interfaces:**
- Consumes: existing artifact response, search response, and public error shape `{error: {message: string}}`.
- Produces: generated section markers, status chip state, active rail links, and safe upload/search error text.

- [x] **Step 1: Add the failing script-contract test**

```python
def test_ui_script_uses_safe_error_messages_and_rail_navigation_state():
    script = Path("static/app.js").read_text()
    assert "data.error?.message" in script
    assert "rail-link" in script
    assert "IntersectionObserver" in script
```

- [x] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_ui_shell.py::test_ui_script_uses_safe_error_messages_and_rail_navigation_state`

Expected: FAIL because the current script reads `data.detail` and has no rail-state observer.

- [x] **Step 3: Update `static/app.js` without changing endpoint calls**

Use the existing render functions and IDs. Change failed API rendering to:

```javascript
const message = data.error?.message || data.detail || "SpeechLens could not complete this request.";
```

Add `rail-link` classes to the anchor markup in Task 1 and a small `IntersectionObserver` that toggles an `is-current` class for the visible report section. Keep `seek()`, `refresh()`, `rename()`, `search()`, and export behavior unchanged. Add a `status--complete` class after a successful upload and `status--error` class after a failed one.

- [x] **Step 4: Run the script-contract test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_ui_shell.py::test_ui_script_uses_safe_error_messages_and_rail_navigation_state`

Expected: PASS.

- [x] **Step 5: Commit the rendering polish**

```bash
git add static/app.js tests/test_ui_shell.py
git commit -m "feat: polish SpeechLens workspace interactions"
```

### Task 4: Verify the complete fixture-mode user flow

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: fixture-mode command documented in README and all existing static/application routes.
- Produces: an explicit note that the editorial workspace is available in fixture mode and preserves the same workflow.

- [x] **Step 1: Update the README UI description**

Add this sentence below the fixture-mode start command:

```markdown
The browser opens an editorial workspace with a left navigation rail for Upload, Overview, Speakers, Search, Transcript, and Artifact; it is the same workflow used for live Sarvam analysis.
```

- [x] **Step 2: Run the complete non-paid suite**

Run: `.venv/bin/python -m pytest -q`

Expected: all default tests pass; the opt-in integration test remains skipped unless explicitly enabled.

- [ ] **Step 3: Run the fixture-mode server and inspect in a real browser**

Browser visual inspection could not be completed because no browser surface was available in this environment. The fixture-mode HTTP smoke test did verify the rendered shell is served, upload completes, search returns results, rename works, and the public artifact remains redacted.

Run:

```bash
SPEECHKIT_FIXTURE_MODE=1 SPEECHKIT_DATA_DIR=/tmp/speechlens-ui-fixture \
  .venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```

Verify: desktop rail anchors scroll correctly; a supported fixture upload reaches the completed workspace; search results and transcript turns seek playback; rename persists after refresh; the narrow viewport collapses the rail; no public artifact JSON contains `media_path`.

- [x] **Step 4: Commit the verification documentation**

```bash
git add README.md
git commit -m "docs: describe SpeechLens editorial workspace"
```

## Plan self-review

- **Spec coverage:** Tasks 1–3 cover the rail, report canvas, visual system, accessibility, responsive behavior, and current interaction flow. Task 4 covers fixture-mode browser verification and user documentation.
- **Scope:** The plan changes only HTML, CSS, JavaScript, one static test, and README copy; no API, schema, backend, or dependency change is included.
- **Consistency:** The IDs used by JavaScript remain stable. Rail targets are defined in Task 1 and consumed in Task 3. All verification commands are executable from the repository root.
