# 14 - Configure provider and model via bot UI

## Behavior

> "User can set the provider and model from Telegram button menus."

## Depends on

01, 03

## Requirements

- A command (e.g. `/settings`) opens a button menu showing the current text provider and
  image provider settings (base_url, model, key) and lets the user edit them.
- Changes are written to `config.json` (via `save_config` from 01) and take effect on the
  next call.
- The optional image provider can be cleared (fall back to the text provider).
- API keys are masked in the UI (never echoed fully back).

## Data and API

- Config: `provider{base_url,model,api_key}`, `image_provider{...}`.

## Technical notes

- Use a small state machine per user (menu → prompt for field → save). Keep it to the
  three fields per provider; do not add unrelated settings here.

## Acceptance checks

- [ ] `/settings` shows the current provider/model and a change persists to `config.json`
      Command: `python -m pytest tests/test_settings.py::test_set_provider -q`
- [ ] Clearing the image provider makes `vision` fall back to the text provider
      Command: `python -m pytest tests/test_settings.py::test_clear_image_provider -q`

## Out of scope for this nanotask

- `nfb setup` (token/group id) — 01.
