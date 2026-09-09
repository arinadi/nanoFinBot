# 07 - OCR: photo → draft

## Behavior

> "System produces a draft from a receipt photo."

## Depends on

04, 01

## Requirements

- `nanofinbot/ocr.py` exposes `photo_to_draft(image_bytes, default_currency) -> Draft`.
- Downloads/prepares the image (Pillow downscale to ≤768px, JPEG q85), calls
  `provider.vision(...)` with a prompt asking for JSON
  `{"amount": ..., "currency": ..., "type": ..., "description": ..., "category": ...}`.
- Validates the returned JSON; on failure returns a Draft with `amount_minor=None`.
- No image bytes are persisted to disk after processing (privacy NFR).

## Data and API

- Uses `provider.vision(...)` from 04 and `CURRENCIES` from 02.
- Function: `photo_to_draft(image_bytes, default_currency) -> Draft`.

## Technical notes

- See `reference/pillow.md` for the 768px cap and `reference/openai-sdk.md` for the
  vision call.
- Convert the LLM's decimal amount to minor units via the currency exponent (same as 05).
- The `category` returned here feeds the auto-create behavior in 11.1.

## Acceptance checks

- [ ] With a mock vision provider returning valid JSON, `photo_to_draft` returns a matching Draft
      Command: `python -m pytest tests/test_ocr.py::test_photo_to_draft -q`
- [ ] With a mock provider returning invalid JSON, the result has `amount_minor=None` and no raise
      Command: `python -m pytest tests/test_ocr.py::test_bad_json -q`
- [ ] No image file is written under the data dir after processing
      Command: `python -m pytest tests/test_ocr.py::test_no_image_persisted -q`

## Out of scope for this nanotask

- Bulk queue of many photos — 10.
- Wiring photo input to the bot — 08.1.
