# SpeechLens editorial workspace UI design

## Goal

Refresh the existing standalone SpeechLens browser UI into an elegant, desktop-first analysis workspace inspired by the supplied reference. The design should make a completed recording feel like a concise investigation report while preserving the current FastAPI endpoints, data shapes, and plain HTML/CSS/JavaScript stack.

## Scope

- Keep the existing single-page application and all current behaviour: upload, Sarvam mode selection, status messages, playback seeking, speaker rename, search, transcript interaction, and artifact export.
- Add a fixed desktop left rail with numbered anchors for Upload, Overview, Speakers, Search, Transcript, and Artifact.
- Restyle the main canvas with measured spacing, compact utility labels, neutral cards, fine dividers, and a single cobalt interaction accent.
- Treat the page as a sequential analysis report: upload first, overview second, then speaker evidence, search evidence, and canonical transcript.
- Collapse the navigation rail to a compact horizontal strip on small screens.

## Visual system

| Token | Value | Use |
| --- | --- | --- |
| Paper | `#f7f7f5` | Page background |
| Surface | `#ffffff` | Panels and input surfaces |
| Ink | `#111111` | Primary text |
| Quiet | `#676767` | Secondary text |
| Rule | `#deded9` | Borders and dividers |
| Cobalt | `#3157e8` | Selection, focus, primary action |
| Warm marker | `#d88b3d` | Quote and playback evidence marker |

Typography uses system sans-serif for dependable local rendering. Headings are heavy, tightly tracked sans-serif; labels, times, counts, and section numbers use a monospace utility face. There are no external font or UI-library dependencies.

## Layout

```text
┌──────────── left rail ────────────┬──────────── analysis canvas ────────────┐
│ SPEECHLENS                         │  01 / OVERVIEW                          │
│ 01 Upload                           │  Recording title + status               │
│ 02 Overview                         │  Player + facts grid                    │
│ 03 Speakers                         │                                         │
│ 04 Search                           │  02 / SPEAKERS   compact profile cards  │
│ 05 Transcript                       │                                         │
│ 06 Artifact                         │  03 / SEARCH     query + evidence cards │
│                                     │                                         │
│ app/version and local mode state    │  04 / TRANSCRIPT ordered canonical turns │
└────────────────────────────────────┴─────────────────────────────────────────┘
```

The rail is navigation, not a second application state: its links scroll to existing page sections. It does not introduce routes, tabs, or a new backend contract.

## Component changes

- **Application shell:** replace the current unconstrained header with a rail and a report canvas; retain the upload form but give it a dedicated opening panel.
- **Overview:** use the existing facts data in an even grid next to the native player. Status becomes a visible chip with safe message text.
- **Speakers:** show the existing metrics in compact bordered cards, with an explicit `Save name` action and quote marker.
- **Search:** retain the existing modes and result data. Make mode/elapsed/result count visibly inspectable, and use a labelled “Play at timestamp” action.
- **Transcript:** preserve canonical ordered segments and click-to-seek; use a rail-like timestamp column and an evidence marker for the active turn.
- **Artifact:** retain the existing JSON `<details>` panel and export button, placed in the section header.

## Behaviour and accessibility

- Existing element IDs remain where JavaScript relies on them.
- Navigation uses standard in-page anchors and visible keyboard focus.
- Buttons and form inputs retain accessible labels.
- Result and transcript interactions remain keyboard-accessible buttons.
- Reduced motion is respected; no animation is required for the design.
- Error rendering reads the new public `error.message` envelope and keeps a safe fallback.

## Out of scope

- No React, external UI library, custom font loading, backend change, API change, new search feature, or new analysis feature.
- No persistent UI preferences, client routing, or mobile drawer implementation.

## Verification

- Run `.venv/bin/python -m pytest -q` to confirm the service contract remains unchanged.
- Start fixture mode without a Sarvam key, upload a supported media filename, then verify navigation anchors, completed rendering, search, rename, transcript seeking, and export in a real browser.
- Verify desktop and narrow viewport presentation with browser screenshots.
