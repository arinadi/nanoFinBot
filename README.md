# nanoFinBot

On-demand Telegram finance bot. Snap a photo of a receipt or type a line of text,
confirm the draft, and nanoFinBot stores an immutable transaction row in SQLite.
No image or document is ever kept — only the extracted data.

## Flow

```mermaid
sequenceDiagram
    participant U as User
    participant G as Telegram Group
    participant B as NanoFinBot

    Note over B: nfb run (server up)
    B->>G: "nanoFinBot ready"

    U->>G: send text (e.g. "spend 50 pizza") or a receipt photo
    G->>B: forward message
    B->>B: parse text / OCR photo → draft
    B->>G: draft summary + [Save] [Edit] [Cancel]

    U->>G: tap Save
    G->>B: callback save:<id>
    B->>B: write immutable transaction (SQLite)
    B->>G: "Saved: …"

    U->>G: /report or /export
    G->>B: command
    B->>G: PDF / CSV document
```

## Install

```bash
git clone <this-repo>
cd nanoFinBot
python install.py
nfb setup
nfb run
```

## Run from the GHCR image

The image stores config and the SQLite database in `/config` and `/data`.
Mount both volumes so the database survives container replacement:

```bash
docker run -d \
  -v nanofinbot-config:/config \
  -v nanofinbot-data:/data \
  ghcr.io/<owner>/nanofinbot:latest run
```

Run `nfb setup` inside a one-off container first to write the token/group id:

```bash
docker run --rm -it -v nanofinbot-config:/config ghcr.io/<owner>/nanofinbot:latest setup
```

## Documentation

The full plan (PRD, architecture, tasks) lives in `nanoFinBot_plan/`.
