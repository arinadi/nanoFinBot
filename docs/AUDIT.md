# nanoFinBot — Security & Quality Audit

Date: 2026-09-10
Method: three independent review sub-agents (security, plan-conformance, code quality), read-only.
Scope: `nanofinbot/`, `install.py`, `Dockerfile`, `.github/workflows/ghcr.yml`, `pyproject.toml`, `tests/`, and the full plan in `nanoFinBot_plan/`.
Baseline: 56 tests pass, `compileall` clean, `pip-audit` clean.

## Summary

| Severity | Count |
|---|---|
| Critical / High | 5 |
| Medium | 4 (some multi-part) |
| Low | 12 |

---

## Critical / High

### H1 — No authorization on any bot command
- **Where:** `nanofinbot/bot.py` (all `@dp.message(Command(...))` handlers and callbacks).
- **Problem:** `cfg.group_id` is only used for outbound messages. No inbound check. Anyone who finds the bot username can `/export`/`/report`/`/list` the ledger, disable rows, rename categories, and — worst — use `/settings` to point `base_url`/`api_key` at an attacker server, exfiltrating every future photo and text.
- **Fix:** one allow-list guard (middleware/filter) covering every handler.

### H2 — Blocking work in async handlers
- **Where:** `bot.py:44` (`cmd_report`), `bot.py:50` (`cmd_export`), `ocr.py:43` (`preprocess`).
- **Problem:** reportlab `doc.build()` and Pillow `thumbnail/save` run synchronously in the event loop; a large ledger or photo freezes the whole bot.
- **Fix:** `asyncio.to_thread(...)` for `build_pdf`, `build_csv`, `preprocess`.

### H3 — `advance_due` yearly rollover on Feb 29 crashes
- **Where:** `db.py:359`.
- **Problem:** `date(d.year + 1, 2, 29)` raises `ValueError` on non-leap years; runs in `recurring.check_due` at startup → bot won't start.
- **Fix:** clamp the day like `_add_month` does (e.g. `min(day, monthrange(year+1, 2)[1])`).

### H4 — Bulk queue is dead code
- **Where:** `bot.py:106-111`.
- **Problem:** photo handler uses `msg.photo[-1]` → `capture.on_photo`; `capture.on_photos` is never called. Multi-photo albums are never queued. Nanotask 10 passes only because tests call `on_photos` directly.
- **Fix:** handle `media_group_id` (aggregate album photos → `on_photos`).

### H5 — No draft-queue resume on restart
- **Where:** `bot.main` (`bot.py:159-168`).
- **Problem:** drafts persist but nothing re-presents pending drafts at startup (architecture §5 risk 4).
- **Fix:** on startup, re-present the oldest pending draft per user.

---

## Medium

### M1 — `config.json` written world-readable
- **Where:** `config.py:111-116`.
- **Problem:** `write_text` → mode 0644; file holds token + API keys.
- **Fix:** `os.chmod(tmp, 0o600)` before `os.replace` (and `0o700` on the dir).

### M2 — Recurring gaps
- **No hourly re-check** — `check_due` runs only at startup (`bot.py:164`); task 13.2 requires a periodic re-check.
- **Advance not idempotent** — `recurring.py:52-58` sends then advances; a crash in between double-fires.
- **`/recurring add` unvalidated** — `bot.py:80` `float(args[2])` crashes on bad input; `type` dropped (always expense); `frequency`/`next_due` never validated.

### M3 — `/report` ignores period
- **Where:** `bot.py:42-45`.
- **Problem:** `list_transactions(status="active")` with no date range, but `build_pdf` labels it "current month" → misleading.
- **Fix:** pass a real current-month `start`/`end`.

### M4 — Missing `None` guards
- **Where:** `bot.py:111,115,137,144`.
- **Problem:** `msg.from_user` / `cq.message` / `cq.from_user` can be `None` (channels, anonymous) → `AttributeError`.

---

## Low

### L1 — Symlink race on temp config write
- `config.py:114-115`: `write_text` follows symlinks; pre-created `config.json.tmp` symlink redirects the write. Fix: `tempfile.mkstemp` + `os.fdopen`, or `O_CREAT|O_EXCL|O_NOFOLLOW`.

### L2 — No decompression-bomb / size cap before image decode
- `ocr.py:24-30`: `Image.MAX_IMAGE_PIXELS` never set; default limit only warns. Fix: set a cap and reject oversized byte payloads.

### L3 — Unbounded numeric input → `inf` → `OverflowError`
- `parser.py:63-71`, `db.py:92-93`, `bot.py:80`: huge numbers produce `inf`; `to_minor` then raises `OverflowError`. Fix: reject non-finite and clamp.

### L4 — Launcher path not shell-escaped
- `install.py:59-67`: venv path interpolated raw into shell/`.cmd`. Fix: `shlex.quote()` (POSIX); proper escaping or rely on the generated `nfb.exe` (Windows).

### L5 — `mask_key` leaks first 3 + last 3 chars
- `settings.py:8-13`: short keys almost fully revealed. Fix: fixed prefix only.

### L6 — `install.py` doesn't guarantee `nfb` on PATH
- `install.py:90`: only prints a hint. Fix: add `~/.local/bin` to the shell profile or fail clearly.

### L7 — Dead code
- `db.set_category` and `db.create_category` have no callers. Remove or test.

### L8 — `Dockerfile` runs as root
- No `USER` directive. Fix: add a non-root user and `chown /config /data`.

### L9 — GHCR tag trigger emits no version tag
- `ghcr.yml`: `tags: ["v*"]` doesn't produce a `v*` image tag (only `latest` + `sha`).

### L10 — `categories.py` module missing (layout drift)
- `code-layout.md` lists `categories.py`; logic lives in `db.py` + UI inlined in `bot.py`.

### L11 — Unbounded in-process state
- `_settings_state` (`bot.py`), `_editing`/`_queue`/`_batch_active` (`capture.py`) are never pruned.

### L12 — Test coverage gaps
- `bot.py` handler wiring untested (only `startup`); `capture.on_photo`/`on_list` negative paths; `recurring.advance_due` daily/weekly/yearly/Feb-29/month-end; `reports._expense_chart` branch; provider error matrix (`ProviderNetworkError`, generic, `ProviderNotConfigured`).

### L13 — Unknown currency code mis-formats
- `db.py:84-100`: unknown code → empty symbol + exponent 0 → `" 5000"` and wrong minor math. Fix: normalize/reject at ingestion.

### L14 — Zero / negative amounts accepted
- OCR can return negative `amount`; `on_save` accepts `amount_minor == 0`. Fix: require positive amount.

---

## Verified clean

- SQL injection: all queries parameterized; no dynamic SQL values.
- No hardcoded secrets in source/logs/workflow; `getpass` for token input.
- Atomic config write (temp + `os.replace`) — apart from L1/M1.
- No image/bytes persisted to disk (privacy NFR holds).
- Provider error mapping correct (401 vs network), key never in messages.
- Path traversal: no file writes from untrusted input.
- GHCR workflow: scoped permissions, no secret leakage.
- Immutability, minor-unit storage, disabled-row exclusion, category dedup, reminder-only, drafts-persist: all conform to plan.
- No out-of-scope features implemented.
