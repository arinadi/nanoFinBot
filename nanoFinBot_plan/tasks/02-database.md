# 02 - SQLite schema and transaction repository

## Behavior

> "System persists transactions in SQLite on first run."

## Depends on

01

## Requirements

- `nanofinbot/db.py` opens the DB at `data_dir()/nfb.db`, sets WAL mode, and creates
  `transactions`, `categories`, and `recurring` tables if absent.
- Transaction repository supports: create (draft), list (optionally filtered by
  status/period), and `set_status` (draft → active, or active → disabled).
- No UPDATE of amount/currency/description/type after a row becomes `active`
  (immutability, `architecture.md` §2). Only `status` may change.
- A single shared connection is used, guarded by an `asyncio.Lock`.

## Data and API

- Entities: Transaction, Category, RecurringItem (see `architecture.md` §2 for fields).
- Functions: `init_db()`, `create_draft(...)`, `list_transactions(...)`,
  `set_status(id, status)`, `create_category(name)`, `list_categories()`.

## Technical notes

- Amounts are INTEGER minor units + ISO code; `CURRENCIES` map (code → symbol, minor
  exponent) lives here or in a shared module, used by parser/reports.
- See `reference/aiosqlite.md`.

## Acceptance checks

- [ ] `init_db()` on a fresh path creates the three tables
      Command: `python -m pytest tests/test_db.py::test_schema -q`
- [ ] `create_draft` then `list_transactions` returns the row with the same fields
      Command: `python -m pytest tests/test_db.py::test_roundtrip -q`
- [ ] `set_status` on an `active` row changes status; there is no update path for amount
      Command: `python -m pytest tests/test_db.py::test_immutable -q`

## Out of scope for this nanotask

- Category auto-create/rename business logic — 11.
- Draft queue/capture logic — 08.
