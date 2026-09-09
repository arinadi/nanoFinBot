# 06 - LLM categorization

## Behavior

> "System assigns a category to a draft using the configured LLM provider."

## Depends on

04, 05

## Requirements

- `nanofinbot/parser.py` gains `categorize(draft) -> str | None`, which asks the
  provider to pick a category for the draft's description/amount.
- Returns the category name, or `None` when there is no provider configured, the call
  fails, or the LLM returns invalid JSON.
- The LLM is asked for JSON (`{"category": "..."}`); the response is validated before use
  (risk chain 1).
- Categorization is skipped entirely when no provider is configured.

## Data and API

- Uses `provider.text(...)` from 04.
- Function: `categorize(draft) -> str | None`.

## Technical notes

- Use `response_format={"type":"json_object"}` and a system prompt that names the
  existing categories and asks for one (or a new one).
- On any failure return `None` (never raise into the capture flow) — the draft simply
  stays uncategorized and the user can Edit.

## Acceptance checks

- [ ] With a mock provider returning `{"category":"Food"}`, `categorize(draft)` returns "Food"
      Command: `python -m pytest tests/test_parser.py::test_categorize_llm -q`
- [ ] With no provider configured, `categorize(draft)` returns None without a network call
      Command: `python -m pytest tests/test_parser.py::test_categorize_no_provider -q`
- [ ] With a mock provider returning invalid JSON, `categorize(draft)` returns None (no raise)
      Command: `python -m pytest tests/test_parser.py::test_categorize_bad_json -q`

## Out of scope for this nanotask

- Auto-creating the category in the DB — 11.1.
- OCR of photos — 07.
