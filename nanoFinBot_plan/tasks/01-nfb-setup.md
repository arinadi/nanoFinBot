# 01 - `nfb setup` configures token and group id

## Behavior

> "User can configure the bot token and group id by running `nfb setup`."

## Depends on

00.1

## Requirements

- `nfb setup` interactively prompts for the Telegram bot token and (optional) group id,
  and writes `config.json` to the platformdirs user config dir.
- Re-running `nfb setup` overwrites cleanly; a missing group id is stored as null.
- Config writes are atomic (write temp file, then rename) — risk chain 6.
- A `nanofinbot/config.py` module provides `load_config()` and `save_config()`, plus
  `config_dir()` / `data_dir()` path helpers used by later tasks.
- On startup, a malformed config produces a clear error message (not a traceback).

## Data and API

- `config.json` shape (see `architecture.md` §2): `telegram_token`, `group_id`,
  `default_currency`, `timezone`, `provider{base_url,model,api_key}`,
  `image_provider{base_url,model,api_key}`.
- Command: `nfb setup`.

## Technical notes

- Use `getpass` for the token input (do not echo secrets), `input()` for group id.
- Default `default_currency` to IDR, `timezone` to `Asia/Jakarta` unless overridden.
- Store `provider`/`image_provider` as empty placeholders; 14 populates them.

## Acceptance checks

- [ ] Running `nfb setup` with piped answers writes `config.json` at the platformdirs path
      Command: `printf "tok123\n\n" | nfb setup && python -c "from nanofinbot.config import load_config; print(load_config().telegram_token)"`
- [ ] `config.json` is written atomically (no partial file if interrupted mid-write)
      Command: `python -m pytest tests/test_config.py -q`

## Out of scope for this nanotask

- Setting provider/model — 14.
- Sending the startup status message — 03.
