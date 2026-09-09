# 05 - Rules-based text parser

## Behavior

> "System parses a text expense message into a draft."

## Depends on

01

## Requirements

- `nanofinbot/parser.py` exposes `parse(text, default_currency) -> Draft`.
- `Draft` carries `amount_minor`, `currency`, `type` (expense/income), `description`,
  `category` (nullable).
- Handles the common shapes: `spend 50 pizza`, `+3500 salary` (income), `paid 20 taxi`,
  `50 coffee`, with a currency symbol or code when present.
- Works with **no LLM key** — pure rules, no network call.
- On unparseable input, returns a Draft with `amount_minor=None` and a reason, rather
  than raising.

## Data and API

- Uses the `CURRENCIES` map (code → minor exponent, symbol) from 02.
- Function: `parse(text, default_currency) -> Draft`.

## Technical notes

- Convert the decimal amount to minor units using the currency's exponent
  (e.g. USD `50` → `5000`; IDR `50000` → `50000`).
- Keep the rules small and predictable; the LLM (06) is the fallback for anything the
  rules miss. The rules path is what keeps text entry working offline (risk chain 2).

## Acceptance checks

- [ ] `parse("spend 50 pizza", "USD")` returns type=expense, amount_minor=5000, desc="pizza"
      Command: `python -m pytest tests/test_parser.py::test_spend -q`
- [ ] `parse("+3500 salary", "IDR")` returns type=income
      Command: `python -m pytest tests/test_parser.py::test_income -q`
- [ ] `parse("hello", "USD")` returns amount_minor=None and does not raise
      Command: `python -m pytest tests/test_parser.py::test_unparseable -q`

## Out of scope for this nanotask

- LLM categorization — 06.
- Wiring text input to the bot — 08.1.
