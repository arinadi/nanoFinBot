# 04 - Provider client (OpenAI-compatible)

## Behavior

> "System calls a configured OpenAI-compatible endpoint and returns the completion."

## Depends on

01

## Requirements

- `nanofinbot/provider.py` exposes an async-friendly client built from the config
  provider settings (`base_url`, `model`, `api_key`).
- `text(prompt, user_input) -> str` calls chat completions and returns the content.
- `vision(prompt, image_bytes) -> str` sends an image as a base64 data URI and returns
  the content.
- The optional `image_provider` config, when present, overrides the provider for
  `vision`; otherwise `vision` uses the same provider (context Q8).

## Data and API

- Config: `provider{base_url,model,api_key}`, `image_provider{...}` (nullable).
- See `reference/openai-sdk.md`.

## Technical notes

- Pass `base_url` and `api_key` explicitly (never rely on env vars).
- Use `openai`'s sync client but call it via `asyncio.to_thread` (or the async client)
  to avoid blocking the bot loop.
- Wrap errors: raise distinct `ProviderAuthError` (401) and `ProviderNetworkError`
  (unreachable) so callers can show the right message (risk chain 2).

## Acceptance checks

- [ ] `text()` against a local mock OpenAI endpoint returns the mocked content
      Command: `python -m pytest tests/test_provider.py::test_text -q`
- [ ] `vision()` uses `image_provider` when configured, else the default provider
      Command: `python -m pytest tests/test_provider.py::test_image_provider_override -q`
- [ ] A 401 maps to `ProviderAuthError`
      Command: `python -m pytest tests/test_provider.py::test_auth_error -q`

## Out of scope for this nanotask

- Parsing/categorization logic — 05/06.
- OCR preprocessing — 07.
