# nanoFinBot — Architectural decision records

Each entry: what was decided, what else was considered, why this won, and what it costs.

## 1. One `openai` SDK for all LLM/OCR providers

- **Decided:** a single `openai` client with a configurable `base_url` drives text and
  vision; an optional `image_provider` overrides the vision target.
- **Considered:** native `google-genai` SDK alongside `openai`; or Cloud Vision for OCR.
- **Why:** Gemini exposes an OpenAI-compatible endpoint, so one client reaches OpenAI,
  Gemini, and local servers with zero per-provider code.
- **Cost:** relies on Gemini's OpenAI-compat layer staying stable; no provider-specific
  features (e.g. Gemini grounding) are usable.

## 2. SQLite over MySQL/PostgreSQL

- **Decided:** SQLite (WAL), single file at the platformdirs data dir.
- **Considered:** MySQL (the user's first mention) and PostgreSQL.
- **Why:** no server process, single file, fits the nano/on-demand target and a 1 GB VPS.
- **Cost:** no multi-process concurrent writes; the design assumes one bot process.

## 3. Amounts as integer minor units + ISO code

- **Decided:** store `amount_minor` (int) + `currency` (ISO 4217); a static
  `CURRENCIES` map holds symbol and minor exponent.
- **Considered:** float/decimal amounts, or a single default currency.
- **Why:** exact arithmetic, multi-currency with no conversion (context Q12).
- **Cost:** the `CURRENCIES` map must be maintained as currencies are added.

## 4. Drafts persist as `status=draft` rows in the transactions table

- **Decided:** a pending confirmation is a Transaction with `status=draft`; Save→active,
  Cancel→delete, Edit→update the draft row only.
- **Considered:** an in-memory draft queue.
- **Why:** an on-demand bot can be killed any time; persisted drafts resume the queue on
  restart (risk chain 4).
- **Cost:** draft rows share the transactions table; reports/list must filter on status.

## 5. Immutable ledger with a `disabled` flag

- **Decided:** `active`/`disabled` rows cannot be edited or deleted; `disabled` only
  excludes the row from reports.
- **Considered:** fully editable transactions, or hard append-only with reversal entries.
- **Why:** matches the user's explicit "saved data cannot be edited" while keeping a
  soft-void for mistakes (context Q14).
- **Cost:** correcting a mistake means disabling and re-logging, not editing in place.

## 6. Editable install (`pip install -e .`) for live updates

- **Decided:** `install.py` creates a venv, installs deps, then `pip install -e .`; the
  `nfb` command always reflects the current repo source.
- **Considered:** a symlink to the repo (fails on Windows without admin/Developer Mode),
  or copying the launcher (stale after `git pull`).
- **Why:** cross-platform (Windows + Linux/proot) and self-updating on `git pull`
  (context Q20).
- **Cost:** the venv must persist at a known path; the repo must remain on disk.

## 7. On-demand PDF/CSV via Telegram instead of a web dashboard

- **Decided:** reports are generated on demand and sent as Telegram documents.
- **Considered:** a Python web server (FastAPI/Flask) bound to a local port.
- **Why:** no always-on process, no open port, no auth to secure — fits the nano target.
- **Cost:** reports are only viewable in chat; no browser UI.

## 8. aiogram 3 over python-telegram-bot

- **Decided:** aiogram 3.x for the bot.
- **Considered:** python-telegram-bot 21.x (also async).
- **Why:** lighter and async-native; long polling and inline buttons are first-class.
- **Cost:** a smaller surrounding ecosystem than python-telegram-bot.
