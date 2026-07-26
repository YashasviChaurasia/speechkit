# SpeechLens Provider Configuration UI Design

## Goal

Add a small standalone reference UI for the existing SpeechKit provider-credential contract.

## Scope

- Fetch `GET /api/provider/config` when the page loads.
- Show only `Configured` or `Not configured`.
- When unconfigured, show a password input with Show/Hide and Save API key.
- When configured, provide Replace and Remove actions.
- Clear the password input after every save attempt.
- Disable Analyse unless configuration is confirmed.
- Use the existing `PUT` and `DELETE /api/provider/config` endpoints. No backend or schema changes.

## Behaviour

The UI submits the password field only to the current origin. It does not put the value in localStorage, URLs, rendered HTML, status text, or application state. A successful save refreshes the safe configuration state, then clears the field. A failed request displays the existing safe server error message and still clears the field.

The copy states that analysis uses real Sarvam credits. This is a standalone behavioural reference: OffCam should implement the same interaction through its same-origin backend proxy, rather than importing this DOM code.

## Verification

A static UI test asserts the configuration controls and client calls. Existing backend contract tests cover the endpoint shapes and verify that a submitted key is never returned.
