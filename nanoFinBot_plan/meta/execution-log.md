# nanoFinBot — Execution Log

## Phase 0 — intake, research, discovery
- Recorded idea verbatim; no reference material in the folder.
- Researched 5 comparable finance bots + OCR/LLM technology (Google Vision vs Gemini OCR, OpenAI-compatible endpoints, Alpine caveat).
- Ran the discovery Q&A (16 questions, one by one with options).
- Selected mode `cli-tool`; design doc skipped.
- 6 features deferred.
- Added requirement: bulk input uses a queue — many photos become separate transactions, confirmed one by one (Save/Edit/Cancel).
- Added requirement: CSV export shares the on-demand Telegram-document path with PDF (one report/export flow).

## Phase 1 — requirements and PRD
- PRD written: 3 core features, 14 base features.
- 3 scope challenges, all resolved with a cheaper alternative (web dashboard→PDF, dedicated OCR→same-LLM default, MySQL→SQLite).
- Clarified install/run model: install.sh runs host-side, extracts the image rootfs, installs `nfb` directly (no container runtime at run time).
- Revised install model: two paths — (a) image (nfb runs inside), (b) source (git clone + install.sh). install.sh symlinks `nfb` to the local repo (not copy) so `git pull` updates are picked up automatically.
- Replaced install.sh with cross-platform install.py (Windows + Linux/proot): creates venv, installs deps, `pip install -e .` (editable) so `nfb` always reflects current source.

## Phase 2 — architecture
- Architecture written: stack pinned (Python 3.12, aiogram 3, openai 1, aiosqlite, reportlab, Pillow, platformdirs), 5 entities, 11 components, 6 risk chains.
- Data model: amounts as integer minor units + ISO currency; transaction status draft→active/disabled (drafts persist in DB).
- Design doc skipped — cli-tool has no UI.

## Phase 3 — decomposition
- Populated reference/ with code layout + aiogram, openai-sdk, gemini-openai-compat, pillow, aiosqlite, reportlab docs.
- Wrote 23 nanotasks (16 majors: 6 split into minors, 10 unsplit).
- Seeded the ledger: all 23 failing.

## Phase 4 — handoff
- Wrote AGENT.md (directive), VERIFY.md (acceptance contract), meta/decisions.md (8 decision records).
- Plan complete. All phases approved.

## Implementation
- Implemented all 23 nanotasks: package scaffold, install.py, config/db/provider/parser/ocr/capture/categories/reports/recurring/settings/bot, plus Dockerfile and GHCR workflow.
- 51 tests pass (`python -m pytest -q`).
- DEVIATION (approved by user): bumped Pillow from `>=10,<11` to `>=12,<13` and pytest to `>=9,<10` / pytest-asyncio `>=1,<2` because Pillow 10.4.0 has high-severity CVEs with no patched 10.x release. `pip-audit` is clean after the bump.
- Task 15 (GHCR image) is `blocked`: no Docker runtime in this environment; Dockerfile and workflow are written but the build could not be verified.
