# 09 - Disable a saved transaction

## Behavior

> "User can disable a saved transaction to exclude it from reports."

## Depends on

08.1

## Requirements

- A command/menu lists recent `active` transactions, and a button disables the chosen
  one (sets status to `disabled`).
- `disabled` transactions are excluded from report/export totals (exercised in 12).
- Disabling is the only change allowed to an `active` row (no edit/delete).

## Data and API

- Uses `set_status(id, "disabled")` from 02.
- Command: e.g. `/list` showing the last N transactions with a Disable button each.

## Technical notes

- This is the soft-void from `architecture.md` §2: the row stays, only report inclusion
  changes (context Q14).

## Acceptance checks

- [ ] Disabling a transaction sets status to `disabled` and it is excluded from the summary
      Command: `python -m pytest tests/test_disable.py::test_disable -q`
- [ ] An `active` transaction still cannot be edited or deleted after this task
      Command: `python -m pytest tests/test_disable.py::test_no_edit_delete -q`

## Out of scope for this nanotask

- Actually generating reports — 12.
