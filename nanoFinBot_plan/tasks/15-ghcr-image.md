# 15 - GHCR image

## Behavior

> "User can run nanoFinBot from the GHCR image."

## Depends on

14

## Requirements

- A `Dockerfile` based on Alpine builds the package and sets `ENTRYPOINT ["nfb"]`.
- A GitHub Actions workflow builds the image and pushes it to GHCR on tag/push to main.
- The image runs `nfb --version` and `nfb run` (with a mounted data dir for the SQLite DB
  and a mounted config).

## Data and API

- Image: `ghcr.io/<owner>/nanofinbot:latest`.
- Volumes: config dir and data dir mounted so the DB survives container replacement.

## Technical notes

- Alpine + Python: use `python:3.12-alpine`; install only pip deps (no native OCR libs —
  OCR is a cloud call). See `reference/gemini-openai-compat.md` for why no local OCR.
- Document the volume mounts in the workflow/README so the DB is not lost on restart
  (risk chain 5).

## Acceptance checks

- [ ] `docker build` succeeds and `docker run --rm <img> --version` prints the version
      Command: `docker build -t nanofinbot:test . && docker run --rm nanofinbot:test --version`

## Out of scope for this nanotask

- `install.py` (source install path) — 00.2.
