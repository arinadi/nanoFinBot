# nanoFinBot — Phase 0 Context

## Initial idea (verbatim)

> "saya punya ide membuat finance bot namanya nanoFinBot. saya mau bentuknya ghcr image agar saya mudah install di proot distro dan install.sh, sepertinya alphine cukup untuk python/go dan database. llm dan ocr (llm mahal untuk gambar) menggunakan google api dan openai support api. setup cukup panggil dari terminal nfb setup untuk isi bot token dan group id (optional). lainnya di config lewat bot ui (button menu). karena bot ondimand maka ketika bot nyala kirim pesan status ke telegram. research fitur yang biasa ada di finance bot"

## Reference material

None. The project folder was empty at intake. All scope below comes from the idea and the Q&A.

## Research findings

### Comparable products

| Product | Does well | Leaves this user unserved |
|---|---|---|
| Finny (finnybot.com, commercial) | Text/voice/photo capture in Telegram, shared group budget | Closed SaaS, data on their server, monthly fee |
| zougar99/Telegram-Finance-Bot (Python) | NL input, budgets, forecasts, charts | Standard Docker (not GHCR/proot), no OCR cost model |
| jagmarques/expensesbot (TypeScript) | Receipt OCR (Google Vision), budgets, recurring | Uses paid Vision + DeepSeek only, not OpenAI-compatible |
| yelinaung/expense-bot (Go) | Gemini OCR, voice, tags, whitelist, GoReleaser | Requires PostgreSQL (heavy for "nano") |
| agunginsani/expenses-tracker (Bun/TS) | Gemini + Google Sheets, IDR, Asia/Jakarta timezone | Data lives in a spreadsheet, not a local DB |

### Common finance-bot features (from research)

Manual expense/income entry, natural-language entry, AI auto-categorization, receipt OCR, budgets with alerts, reports (daily/weekly/monthly) with charts, export (CSV/JSON/PDF), multi-currency, recurring transactions, category management, voice input, shared group tracking.

### Technology notes

- **OCR cost.** Google Cloud Vision OCR ~$1.50/1000 images, 1000/month free tier, deterministic + confidence scores. Gemini vision is cheaper per page (~$0.33/1000 Flash-Lite) but token-billed (output tokens dominate) and non-deterministic with no confidence. Decision below (Q: OCR provider).
- **OpenAI-compatible API.** Gemini exposes an OpenAI-compatible Chat Completions endpoint. One client with configurable `base_url` + `model` + `key` can reach OpenAI, Gemini, or a local/compatible server.
- **Alpine caveat.** Alpine is musl-based; native OCR/ML wheels won't build locally. Not a problem here because OCR/LLM are cloud calls (Google/OpenAI), and SQLite needs no server. This fits the "nano" target.
- **Polling vs webhook.** proot-distro runs behind NAT on a phone/desktop, so Telegram long polling (`getUpdates`) is the right transport; no public webhook URL needed.

## Mandatory questions and answers

1. **Why does this exist?** (verbatim) "lainnya mahal dan ribet. nanofinbot setup sederhana dan perational mudah. cukup upload foto nota, slip gaji, transfer atau ketik native lang. dan report rapi di web base dan bisa export. target deploy proot distro atau vps kecil. tidak ada gambar dan doc yang disimpan. setelah dibaca maka cuma data yang di simpan ke db. db boleh mysql atau yang lebih ringan."
   — Alternatives are expensive and complicated; nanoFinBot is simple to set up and run. Upload receipt/salary-slip/transfer photos or type natural language; neat reports + export; deploy to proot-distro or a small VPS; **no images/documents are stored** — only extracted data goes to the DB.
2. **Who is the specific user?** "Me + family/group (shared)" — a shared group ledger: multiple people log to one pool.
3. **The one feature that makes this viable:** "Photo → transaction (OCR)" — upload a receipt/slip/transfer photo, the bot reads it and records the transaction.
4. **Landscape:** Greenfield (new).
5. **How do we know it worked?** (verbatim) "proot distro run, bot langsung jalan. proot distro login - nfb setup input bit token, group id, bot langsung mengirim status. setting provider dan model lewat telegram. menu button interaktif. user kirim foto atau natural lang langsung di katagorikan, di konfirmasi, ada tombol save dan edit dan cancel. data yang di save tidak bisa di edit."
   — Binary criterion derived: on a fresh proot-distro, `install.sh` + `nfb setup` (token + group id) yields a running bot that sends a status message; sending a photo or natural-language text produces a categorized transaction with Save/Edit/Cancel buttons; saved data is immutable.

## Project-specific questions and answers

| # | Question | Answer |
|---|---|---|
| 6 | Language | Python (Recommended) |
| 7 | Database | SQLite (Recommended) |
| 8 | OCR provider | Same as the LLM by default (cheap). Optional separate image provider/model. |
| 9 | "OpenAI support API" meaning | Configurable OpenAI-compatible endpoint (`base_url` + `model` + `key`) |
| 10 | Works without LLM key? | Yes — manual text entry parses with rules only |
| 11 | v1 features | Reports (web + chat), Export CSV, Category management, Recurring. Categories can be auto-created by the bot, user can edit them. |
| 12 | Currency | Multi-currency, no conversion |
| 13 | Web report | On-demand PDF sent via Telegram (lighter than a web server) |
| 14 | Edit/delete rule | Fully immutable (no edit, no delete), but a transaction can be **disabled** (excluded from reports) |
| 15 | Running model | On-demand — started via `pd run` (proot-distro) or the `nfb` binary |
| 16 | Recurring timing | Reminder only, no auto-entry — bot reminds the group when a recurring item is due |
| 17 | Bulk input | Queue mode — uploading many photos at once creates a queue of separate transactions; each is confirmed one by one with Save/Edit/Cancel |
| 18 | Export path | CSV export uses the same on-demand flow as PDF — generated and sent as a Telegram document, one shared report/export path |
| 19 | Install/run model | Two install paths: (a) **image** — run the GHCR image, `nfb` runs inside it directly; (b) **source** — `git clone` the repo, then `install.py` installs `nfb` on the host. `install.py` replaces `install.sh` and is cross-platform (Windows + Linux/proot) |
| 20 | Update mechanism | `install.py` creates a venv, installs all deps, then `pip install -e .` (editable). The `nfb` command always reflects the current repo source, so a `git pull` is picked up automatically — no symlink or copy |

## Selected project mode

**`cli-tool`** — the product is a Telegram bot service distributed as a CLI (`nfb`) + GHCR image + `install.sh`, not a web/mobile app. Validation defaults (integration tests, smoke tests, distribution check) map directly: distribution = `install.sh`/image runs; smoke = bot starts and sends status; integration = photo/NL → categorized transaction → save.

**Design document: skipped** (no web/mobile UI; the only UI is Telegram button menus and an on-demand PDF).

## Constraints

- **Team:** 1 (solo).
- **Budget:** minimal — self-hosted on an existing proot-distro / small VPS; cloud costs are only per-image/per-token LLM/OCR usage.
- **Timeline:** not stated.
- **Regulatory:** none identified — personal/shared finance, self-hosted, no images or documents stored (only extracted data), no payment processing.
- **Runtime target:** Alpine Linux (musl), low-memory (fits a 1GB VPS).

## Asset audit

Greenfield — nothing to audit or preserve.

## Deferred features

| Feature | Reason |
|---|---|
| Budgets + alerts | Not selected for v1; reports meet the underlying need |
| Voice input | Not selected; photo + NL text cover entry |
| Web dashboard | Replaced by on-demand PDF via Telegram (lighter, no server/port/auth) |
| Currency conversion | User chose multi-currency without conversion |
| Recurring auto-entry | Replaced by reminder-only (on-demand bot has no scheduler) |
| Bank API auto-import | Not requested; local photo/NL entry covers the need |
