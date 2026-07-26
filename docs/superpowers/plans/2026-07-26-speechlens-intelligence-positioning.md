# SpeechLens Intelligence Positioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Present SpeechLens as a speech-intelligence layer for the Agentic Video Editor.

**Architecture:** Update only the existing hero markup and styles. The browser application, routes, and data flow remain unchanged.

**Tech Stack:** Plain HTML, CSS, pytest.

## Global Constraints

- Frontend presentation copy only.
- Do not add API calls, controls, state, or backend changes.
- Preserve the current upload and analysis workflow.

---

### Task 1: Hero positioning copy

**Files:**
- Modify: `static/index.html`
- Modify: `static/styles.css`
- Test: `tests/test_ui_shell.py`

**Interfaces:**
- Consumes: existing `.intro` hero.
- Produces: `#intelligence-benefits` as static demo copy.

- [x] **Step 1: Write the failing static UI test**

```python
def test_hero_positions_speechlens_as_intelligence_layer():
    html = Path("static/index.html").read_text()
    assert "Speech Intelligence Layer" in html
    assert 'id="intelligence-benefits"' in html
    assert "Agentic Video Editor" in html
```

- [x] **Step 2: Run the focused test and verify it fails**

Run: `.venv/bin/python -m pytest tests/test_ui_shell.py -q`
Expected: FAIL because the hero does not include the intelligence positioning.

- [x] **Step 3: Add the minimum static hero copy and benefit styling**

```html
<p id="intelligence-benefits">Search conversations, verify who said what, and send timestamped evidence to an Agentic Video Editor.</p>
```

- [x] **Step 4: Run the focused test and full suite**

Run: `.venv/bin/python -m pytest tests/test_ui_shell.py -q && .venv/bin/python -m pytest -q`
Expected: all tests pass.

- [x] **Step 5: Commit**

```bash
git add static/index.html static/styles.css tests/test_ui_shell.py docs/superpowers/plans/2026-07-26-speechlens-intelligence-positioning.md
git commit -m "feat: position SpeechLens as speech intelligence"
```
