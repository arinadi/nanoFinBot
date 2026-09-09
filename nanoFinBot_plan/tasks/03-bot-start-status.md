# 03 - Bot starts and sends a startup status message

## Behavior

> "System sends a status message to the group when the bot starts."

## Depends on

01

## Requirements

- `nanofinbot/bot.py` builds an aiogram `Bot` and `Dispatcher`, starts long polling,
  and sends one status message to the configured group id on startup.
- `nfb run` (or the default `nfb` command) starts the bot.
- If no `group_id` is configured, the status message is skipped without error.
- The status text includes the bot name/version.

## Data and API

- Uses `config.telegram_token` and `config.group_id`.
- Command: `nfb run`.

## Technical notes

- Long polling (`dp.start_polling`), never a webhook — proot-distro has no public URL.
- The status send is the observable; in tests, use a fake `Bot` whose `send_message`
  records calls (assert exactly one on startup) — see `reference/aiogram-3.md`.
- Send the status inside the startup hook before entering the polling loop.

## Acceptance checks

- [ ] Starting the bot against a fake Bot sends exactly one message to the group id
      Command: `python -m pytest tests/test_bot.py::test_startup_status -q`
- [ ] Starting with `group_id=null` sends nothing and does not crash
      Command: `python -m pytest tests/test_bot.py::test_no_group -q`

## Out of scope for this nanotask

- Message handlers (text/photo) — 05/07/08.
- Button menus — 14.
