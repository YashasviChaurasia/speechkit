# SpeechKit keychain credential contract design

## Goal

Move Sarvam API-key ownership from environment configuration to the operating-system credential store, and expose a small demo-only configuration contract for an OffCam backend proxy.

## Decisions

- Use the Python `keyring` package with service name `speechkit` and account name `sarvam`.
- Do not read, write, migrate, or fall back to `SARVAM_API_KEY`, `.env`, SQLite, JSON, localStorage, or an encrypted file.
- Add unauthenticated demo-only endpoints at `/api/provider/config`. They return configuration state only, never a key.
- Preserve offline fixture mode: it requires no credential and makes no Sarvam request.
- Resolve the key at the start of each live upload and construct the Sarvam SDK provider only for that request.
- Return `sarvam_not_configured` when no stored key exists, and retain stable `sarvam_authentication` when Sarvam rejects a saved key.

## Contract

```text
GET    /api/provider/config  → {"provider":"sarvam","configured":true|false}
PUT    /api/provider/config  ← {"api_key":"..."} → configuration state only
DELETE /api/provider/config  → {"provider":"sarvam","configured":false}
```

`PUT` accepts a non-blank key once. Its response, errors, logs, OpenAPI examples, fixtures, and persisted data never include the submitted value. Keychain access failures use the existing safe public error envelope with `credential_store_unavailable`.

## Boundaries

The standalone SpeechLens UI does not gain a credential form in this slice. OffCam is responsible for its password input, show/hide control, save/replace/remove controls, browser-memory discipline, configured state display, and disabling Analyse until its server-side proxy reports `configured: true`.

These endpoints are unauthenticated only for the requested local demo. They must not be exposed directly on a public deployment; an OffCam backend proxy or network isolation is required before production use.
