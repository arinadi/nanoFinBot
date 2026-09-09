# Acceptance Contract: nanoFinBot

> Written by nanoPRD Phase 4. This file decides whether the work is accepted.
>
> The implementing agent does not edit this file. An agent that can edit its own
> acceptance criteria has no acceptance criteria.

Every entry below is pass or fail. No entry says "review manually" without stating what
the reviewer is looking for and what makes it a failure.

## How to run everything

Run from the repo root, in order:

```bash
python -m compileall -q nanofinbot
python -m pytest -q
pip-audit
python install.py && nfb --version
docker build -t nanofinbot:test . && docker run --rm nanofinbot:test --version
```

All commands must exit 0. `docker` is skipped only if the container runtime is not
available; in that case the GHCR nanotask (15) is `blocked`, not `passing`.

## Whole-system checks

Must pass regardless of which nanotask was last touched.

| Check | Command | Pass condition |
|---|---|---|
| Syntax/build | `python -m compileall -q nanofinbot` | exit 0 |
| Test suite | `python -m pytest -q` | exit 0, no skipped tests |
| Dependency audit | `pip-audit` | no high or critical findings |
| Distribution (source) | `python install.py && nfb --version` | exit 0, version printed |
| Distribution (image) | `docker build -t nanofinbot:test . && docker run --rm nanofinbot:test --version` | exit 0, version printed |

## Per-nanotask checks

**Not listed here.** Each nanotask's acceptance checks live in its own file under
`nanoFinBot_plan/tasks/`, written once. Their pass/fail state lives in the ledger at
`nanoFinBot_plan/meta/progress.json`. Copying them here would create a second set that
drifts from the first.

To review nanotask state:

```bash
python -c "import json; d=json.load(open('nanoFinBot_plan/meta/progress.json')); [print(t['id'], t['status'], '|', t['behavior']) for t in d['nanotasks'] if t['status'] != 'passing']"
```

This must print nothing (every entry `passing`). A behavior split into minors is not
done until every minor under it passes: `08.1` passing while `08.2` is failing means
behavior `08` is not delivered.

## Non-functional checks

Measurable requirements from `PRD.md` §7, each with its measuring command.

| Requirement | Target | Command | Pass condition |
|---|---|---|---|
| Install works | `install.py` succeeds on a clean env | `python install.py && nfb --version` | exit 0 |
| No image persistence | image temp dir empty after processing | `python -m pytest tests/test_ocr.py::test_no_image_persisted -q` | exit 0 |
| Rules-only parse latency | p95 < 200 ms for `spend 50 pizza` | `python -m pytest tests/test_parser.py -q` (timing assertion in the test) | exit 0 |
| Startup status | exactly one status message on start | `python -m pytest tests/test_bot.py::test_startup_status -q` | exit 0 |
| Privacy | no file containing image bytes remains after any capture | `python -m pytest tests/test_ocr.py tests/test_capture.py -q` | exit 0 |

Memory footprint (idle RSS < 200 MB) is measured manually once by the reviewer with
`ps -o rss= -p <bot pid>`; a value ≥ 200 MB is a failure.

## Regression checks

Greenfield — no prior system. This section is intentionally empty.

## Sign-off

The project is accepted when every check above passes and the success criteria in
`nanoFinBot_plan/PRD.md` §8 are met.

| | |
|---|---|
| Checks passing |  /  |
| Success criteria met |  |
| Accepted by |  |
| Date |  |
