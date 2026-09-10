# nanoFinBot — Fix Plan

Based on `AUDIT.md`. Every finding is mapped to a concrete change. Preferences applied:
group-chat-only authorization (deny-all when nothing configured), unknown currency → fall back
to default, zero/negative amounts → reject.

Legend: `[H]` High, `[M]` Medium, `[L]` Low.

## 1. Authorization [H1]
- New `nanofinbot/security.py`: `authorized(cfg, chat_id) -> bool` = `cfg.group_id is not None and chat_id == cfg.group_id`.
- New `AuthMiddleware(BaseMiddleware)`; registered on `dp.update.outer_middleware` so every
  `Message` and `CallbackQuery` is gated. Unauthorized updates are silently dropped.
- `tests/test_security.py`: authorized() True only for the matching group chat; False for DM/other chat/None.

## 2. Offload blocking work [H2]
- `bot.py`: `cmd_report`/`cmd_export` call `await asyncio.to_thread(reports.build_pdf/build_csv, rows)`.
- `ocr.py`: `processed = await asyncio.to_thread(preprocess, image_bytes)`.

## 3. `advance_due` yearly Feb-29 crash [H3]
- `db.py`: add `_add_year()` with `calendar.monthrange` day-clamp; use in the `yearly` branch.

## 4. Wire the bulk queue [H4]
- `bot.py` photo handler: if `msg.media_group_id` is set, buffer the image and flush after ~1s
  via `capture.on_photos(...)`; otherwise call `capture.on_photo(...)`.

## 5. Draft resume on restart [H5]
- `capture.py`: add `resume_pending(bot, chat_id)` — present the oldest pending draft, queue the
  rest for that user.
- `bot.main`: call it after startup when `group_id` is set.

## 6. Config file permissions + symlink-safe write [M1, L1]
- `config.py` `save_config`: write via `tempfile.mkstemp(dir=p.parent)` + `os.fdopen`, `os.chmod(0o600)`,
  `os.replace`; `os.chmod(config_dir, 0o700)`.

## 7. Recurring fixes [M2]
- `recurring.py` `check_due`: advance `next_due` **before** sending (idempotent — no double-fire).
- `bot.py`: hourly background task calls `check_due`.
- `bot.py` `cmd_recurring`: validate amount (finite/positive via `db.valid_minor`), normalize
  currency, validate `frequency` in `{daily,weekly,monthly,yearly}`, validate `next_due`
  (`date.fromisoformat`), accept optional `type`.

## 8. `/report` period [M3]
- `bot.py` `cmd_report`: compute current-month `start`/`end` (UTC) and pass to `list_transactions`.

## 9. None guards [M4]
- `bot.py`: guard `msg.from_user`, `cq.from_user`, `cq.message` being `None`.

## 10. Pillow decompression / size caps [L2]
- `ocr.py`: set `Image.MAX_IMAGE_PIXELS`; reject payloads over a byte cap; catch decode errors →
  draft with `reason`.

## 11. Amount + currency validation [L3, L13, L14]
- `db.py`: `to_minor` raises on non-finite / too-large; add `valid_minor(amount, code) -> int|None`
  (returns positive minor or None) and `normalize_currency(code, default)`.
- `parser.py` / `ocr.py`: use `valid_minor` + `normalize_currency`; non-positive/unknown-currency → fallback/None.
- `capture.py` `on_save`: require `amount_minor > 0`.
- `bot.py` `/recurring add`: use `valid_minor`.

## 12. Launcher path quoting [L4]
- `install.py`: `shlex.quote()` for POSIX launcher; escape `%`→`%%` for the Windows `.cmd`.

## 13. `mask_key` [L5]
- `settings.py`: show only `key[:4] + "…"` (or `"****"` for short keys).

## 14. `install.py` PATH guarantee [L6]
- POSIX: append `~/.local/bin` to `~/.profile` if missing (idempotent). Windows: print a `setx PATH` hint.

## 15. Dead code [L7]
- `db.py`: remove `set_category` and `create_category`.

## 16. Non-root Docker image [L8]
- `Dockerfile`: `adduser`, `chown /config /data`, `USER`.

## 17. GHCR version tags [L9]
- `ghcr.yml`: add `docker/metadata-action` for `branch`/`tag`/`sha` tags.

## 18. `categories.py` module [L10]
- New `nanofinbot/categories.py` with `on_categories(bot, chat_id)` and `on_rename(bot, chat_id, text)`.
- `bot.py` `/categories` and `/rename` handlers call them.

## 19. Prune in-process state [L11]
- `capture.py`: clear the `_editing` entry for a draft's user on save/cancel.

## 20. Tests [L12]
- Add/extend: `test_security.py` (authorization); `test_db.py` (`advance_due` daily/weekly/yearly/Feb-29/month-end,
  `valid_minor`, `normalize_currency`); `test_parser.py` (positive-only, currency fallback);
  `test_ocr.py` (currency fallback, negative rejected); `test_provider.py` (network/generic/not-configured);
  `test_settings.py` (mask); `test_capture.py` (save-zero rejected); `test_recurring.py` (idempotent advance).
- Run full suite + `compileall` + `pip-audit` after.

## Out of scope (deliberately unchanged)
- `reportlab`/`Pillow`/`pytest` pins (already bumped; recorded in `execution-log.md`).
- Reminder `type`-only edge cases beyond the validations above.
