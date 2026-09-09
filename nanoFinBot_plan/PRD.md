# PRD: nanoFinBot

> Written by nanoPRD Phase 1. Source of truth for requirements.
>
> Architecture decisions live in `architecture.md`. The Phase 0 record — the idea
> verbatim, references read, research findings, and the answers as given — lives in
> `meta/context.md`. Do not restate either here.
>
> This document analyses that record. If a sentence would read identically in
> `meta/context.md`, cite it instead of copying it.

## 1. Problem

The user's alternatives are "expensive and complicated" (context Q1). The concrete
cost is: logging a shared family's money is either a paid cloud SaaS the user does
not control, or a self-hosted bot that demands a PostgreSQL server, a spreadsheet
attachment, or a build toolchain the user has to maintain. For a solo operator on a
proot-distro or a 1 GB VPS, none of those fit.

What changes when this is fixed: the user logs money by snapping a photo of a
receipt, salary slip, or transfer, and gets a clean on-demand report — with no
image or document ever stored, only the extracted rows in a local SQLite file.

## 2. User

A solo self-hoster running a shared household group (context Q2). They operate
on-demand from a phone/desktop proot-distro or a small VPS, are comfortable with a
terminal but want zero ongoing maintenance, and tolerate no always-on process they
have to babysit or secure. This means: long polling (no public webhook URL), SQLite
(no DB server), and a single `nfb` binary for both setup and run.

## 3. Differentiation

nanoFinBot is the only finance bot that runs on-demand from a proot-distro or tiny
VPS, stores **no image or document** (only extracted rows in SQLite), and installs
with one command — differing from Finny (closed cloud SaaS) and from the self-hosted
bots that require PostgreSQL (yelinaung/expense-bot) or a Google Sheet
(agunginsani/expenses-tracker).

## 4. Core features

| Feature | Why it is core | Serves Phase 0 core? |
|---|---|---|
| Photo → transaction (OCR) | The one capability from Q3: photo of a receipt/slip/transfer becomes a categorized transaction | Yes |
| Immutable append-only ledger | Saved rows cannot be edited or deleted, only disabled; no other researched bot does this | Yes |
| No image/document storage | Images are read and discarded; only extracted data persists — the privacy differentiator | Yes |

## 5. Base features

- **Distribution**: GHCR image + `install.py` on Alpine, two install paths (context Q19): **(a) image** — run the GHCR image, `nfb` works inside it directly; **(b) source** — `git clone` the repo, then `install.py` installs `nfb` on the host. `install.py` is cross-platform (Windows + Linux/proot), creates a venv, installs all deps, then `pip install -e .` so the `nfb` command always reflects the current source (a `git pull` is picked up automatically — no copy or symlink) (context Q20).
- **Setup**: `nfb setup` prompts for bot token and (optional) group id.
- **Startup status**: bot sends a status message to the configured group on start.
- **Natural-language text entry**: `spend 50 pizza` → parsed and categorized, rules-only (no LLM key required).
- **LLM parsing/categorization**: configurable OpenAI-compatible endpoint (`base_url` + `model` + `key`); a text provider, plus an optional dedicated image provider that defaults to the text provider (context Q8–Q9).
- **Bulk queue**: many photos at once → a queue of separate transactions, confirmed one by one (context Q17).
- **Confirmation flow**: each draft shows Save / Edit / Cancel buttons (context Q5).
- **Category management**: bot can auto-create categories; user can rename them (context Q11).
- **Multi-currency**: per-transaction currency code, no conversion (context Q12).
- **Reports**: on-demand PDF sent as a Telegram document (context Q13).
- **Export**: CSV, on the same on-demand Telegram-document path as PDF (context Q18).
- **Recurring**: reminders when an item is due; no auto-entry (context Q16).
- **Disable transaction**: mark a saved row disabled so it is excluded from reports (context Q14).
- **Config UI**: provider/model settings via Telegram button menus (context Q5).

## 6. User flow

```mermaid
flowchart TD
    A[Start nfb] --> B[Long-poll Telegram]
    B --> C[Send status to group]
    C --> D{User input}
    D -->|text| E[Rules or LLM parse + categorize]
    D -->|photo(s)| F[OCR via provider -> draft per photo]
    E --> Q[Queue of drafts]
    F --> Q
    Q --> G[Present draft 1-by-1: Save / Edit / Cancel]
    G -->|Edit| H[User edits fields]
    H --> G
    G -->|Cancel| I[Drop draft]
    G -->|Save| J[Write immutable row to SQLite]
    J --> K{Queue empty?}
    K -->|no| G
    K -->|yes| L[Done]
    J -.-> M[Report: PDF or CSV, sent via Telegram]
```

## 7. Non-functional requirements

| Requirement | Target | Measured by |
|---|---|---|
| Install works | `install.py` succeeds on a clean Alpine (and Windows), bot starts | distribution smoke test in a clean environment |
| No image persistence | image temp dir empty after processing | pytest asserts dir contents == 0 post-processing |
| Rules-only parse latency | p95 < 200 ms for `spend 50 pizza` | pytest timing benchmark |
| Memory fit | idle bot RSS < 200 MB | `ps -o rss=` check |
| Startup status | exactly one status message on start | integration test against a mocked Telegram |
| Privacy | no file containing image bytes remains after any capture | pytest test over the temp/storage paths |

## 8. Success criteria

| Criterion | Threshold | Measured from |
|---|---|---|
| Fresh install works | `install.py` + `nfb setup` yields a running bot that sends a status message | clean proot-distro, Q5 |
| Photo becomes a record | a receipt photo produces a correctly categorized draft with Save/Edit/Cancel; Save writes an immutable row visible in the report | Q3 + Q5 |
| No image stored | after processing, zero image/document files on disk | privacy requirement |
| Rules-only entry | text entry works with no LLM key configured | Q10 |

## 9. Out of scope

Phase 0 deferrals are in `meta/context.md` (budgets, voice input, web dashboard,
currency conversion, recurring auto-entry, bank auto-import). Nothing new deferred
in Phase 1.

## 10. Scope challenges

| Feature requested | Underlying need | Alternative offered | Outcome |
|---|---|---|---|
| Web dashboard ("report rapi di web base") | Neat, shareable reports | On-demand PDF sent via Telegram — no server, port, or auth | Accepted PDF |
| Dedicated Google OCR provider ("LLM mahal untuk gambar") | Cheap, reliable image reading | Same provider as the LLM by default, optional separate image provider — research showed Gemini vision is already cheap | Accepted |
| MySQL database ("db boleh mysql") | Reliable storage | SQLite — single file, no server, fits the nano target | Accepted SQLite |
