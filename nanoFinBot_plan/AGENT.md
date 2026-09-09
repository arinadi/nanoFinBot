# Agent Directive: nanoFinBot

> Written by nanoPRD Phase 4. Hand this file to your coding agent.
> Acceptance criteria live in `VERIFY.md`. Do not edit that file.

## Role

You are implementing nanoFinBot — an on-demand Telegram finance bot (Python, SQLite,
Alpine) that turns photos and text into an immutable transaction ledger, distributed
as a GHCR image and an `install.py` source install. The plan is complete. Your job is
to execute it one nanotask at a time, not to redesign it.

If you find a genuine problem with the plan, stop and report it. Do not route around
it silently.

## Reading order

Read these in order. Do not read the whole plan up front — it fills your context before
any work starts. Paths are relative to the repo root.

| When | Read |
|---|---|
| Once, at the start | `nanoFinBot_plan/PRD.md`, `nanoFinBot_plan/architecture.md` |
| Once, at the start | `nanoFinBot_plan/reference/code-layout.md` |
| At the start of every session | `nanoFinBot_plan/meta/progress.json` — what is still failing |
| Before each nanotask | `nanoFinBot_plan/tasks/NN-*.md` or `nanoFinBot_plan/tasks/NN.M-*.md` for that nanotask only |
| Before each nanotask | The code produced by the nanotasks it depends on |
| As needed | `nanoFinBot_plan/reference/` for API and library documentation |
| Never | `nanoFinBot_plan/meta/context.md` — Phase 0 provenance, not implementation input |

## The ledger

`nanoFinBot_plan/meta/progress.json` holds one entry per nanotask. **Every entry
starts `"status": "failing"`.** That is the work list: these are the things that must
become true.

- Flip an entry to `passing` only when every acceptance check in that nanotask file
  passes. Updating the ledger is part of finishing a nanotask, not an afterthought.
- Set `blocked` with a reason rather than skipping an entry.
- Never delete an entry, and never edit a `behavior` string. That would redefine what
  you were asked to build.

## Context recovery

**Before starting a nanotask, re-read the code produced by the nanotasks it depends
on. Do not rely on your memory of code you wrote earlier in this session.**

Twenty turns into an implementation, your memory of what you built is compressed and
lossy. You will re-implement a helper you already wrote, use an old function
signature, or duplicate a type. Re-reading costs a few thousand tokens. Not re-reading
costs a rewrite.

## Conventions

| Concern | Convention |
|---|---|
| Source layout | `nanofinbot/` package, one module per component (see `nanoFinBot_plan/reference/code-layout.md`) |
| File naming | snake_case modules; tests mirror module names as `tests/test_<module>.py` |
| Test location | `tests/`, with async fixtures in `tests/conftest.py` |
| Imports | absolute imports (`from nanofinbot.db import ...`); no wildcard imports |
| Async | async throughout; `aiosqlite` for DB, `aiogram` for the bot |
| Amounts | integer minor units + ISO 4217 code; never floats (`architecture.md` §2) |

## Data initialization

- No migrations or seed data. The schema is created automatically by `init_db()` on
  first run (nanotask 02).
- Config lives in a JSON file at the platformdirs user config dir, written by
  `nfb setup` (nanotask 01). No environment variables carry secrets.
- Test fixtures in `tests/conftest.py`: a tmp config dir, a tmp DB path, a fake
  aiogram `Bot` (records `send_message` calls), and a mock OpenAI-compatible endpoint
  (HTTP server or monkeypatched client). Never hard-code or commit real tokens/keys.

## Validation commands

| Check | Command |
|---|---|
| Test suite | `python -m pytest -q` |
| Smoke (startup status) | `python -m pytest tests/test_bot.py::test_startup_status -q` |
| Syntax/build check | `python -m compileall -q nanofinbot` |
| Dependency audit | `pip-audit` (install via `pip install pip-audit`) |
| Distribution (source) | `python install.py && nfb --version` |
| Distribution (image) | `docker build -t nanofinbot:test . && docker run --rm nanofinbot:test --version` |

## Per-nanotask loop

1. Read the nanotask file and the code it depends on.
2. Implement. Stay inside the stated behavior — the "Out of scope" section is binding.
3. Run every validation command that applies.
4. Run the nanotask's acceptance checks.
5. Self-reflect (below).
6. Flip the ledger entry in `nanoFinBot_plan/meta/progress.json` to `passing`.
7. Stop and request review. Do not start the next nanotask.

Nanotasks are numbered `NN` (a whole behavior) or `NN.M` (one increment of one). Work
them in numeric order, major first and minor second. A behavior split into minors is
not done until every minor under it passes — do not report the behavior complete at
`08.1` while `08.2` and `08.3` remain.

## Self-reflection

Before requesting review, check your own work for:

- Logic duplicated from a dependency nanotask
- Missing input validation on anything crossing a trust boundary (especially LLM/OCR
  JSON responses — see `architecture.md` risk chain 1)
- Missing error handling on any call that can fail (provider 401 vs network timeout)
- Secrets, tokens, or credentials in source
- Image bytes or API keys written to disk or logged (privacy requirement)

## Acceptance gate

A nanotask is done when every validation command passes, every acceptance check in its
file passes, and `pip-audit` reports no high or critical findings. Not before.

## Failure protocol

Maximum three attempts at the same failing check.

After the third, stop. Revert the working tree to the last good state. Report what you
tried, what failed, and what you need. Grinding on attempt seven produces damage, not
progress.

## Evaluation loop

Every three nanotasks, pause and check the whole system against `nanoFinBot_plan/PRD.md`
rather than against the individual nanotask. Drift accumulates below the threshold of
any single check.
