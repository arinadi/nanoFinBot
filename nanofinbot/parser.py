"""Rules-based parsing and LLM categorization for text input."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from nanofinbot.config import DEFAULT_CURRENCY
from nanofinbot.db import CURRENCIES, get_symbol, to_minor
from nanofinbot.provider import Provider, ProviderError

_SYMBOL_TO_CODE = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "฿": "THB",
    "₱": "PHP",
    "₫": "VND",
    "₩": "KRW",
}

_INCOME_WORDS = {
    "income", "salary", "gaji", "received", "refund", "bonus", "cashback",
    "reimburse", "reimbursement", "jual", "sold", "earn", "masuk", "dapet",
}

_STRIP_WORDS = {
    "spend", "spent", "paid", "pay", "buy", "bought", "beli", "bayar", "makan",
    "belanja", "cost", "fee", "ongkir", "parkir", "for", "on", "at", "the", "a",
    "an", "with", "to", "of", "in", "and", "transport",
}

_NUMBER_RE = re.compile(r"\d[\d,]*\.?\d*")


@dataclass
class Draft:
    amount_minor: int | None = None
    currency: str = DEFAULT_CURRENCY
    type: str = "expense"
    description: str = ""
    category: str | None = None
    source: str = "text"
    reason: str | None = None


def _detect_currency(text: str, default: str) -> str:
    upper = text.upper()
    for code in CURRENCIES:
        if re.search(rf"(?<![A-Z0-9]){re.escape(code)}(?![A-Z0-9])", upper):
            return code
    lower = text.lower()
    if re.search(r"\brp\b", lower) or re.search(r"^rp\s*\d", lower):
        return "IDR"
    for sym, code in _SYMBOL_TO_CODE.items():
        if sym in text:
            return code
    return default


def _extract_amount(text: str) -> float | None:
    m = _NUMBER_RE.search(text)
    if not m:
        return None
    raw = m.group(0).replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


def _extract_description(text: str, code: str) -> str:
    s = text
    sym = get_symbol(code)
    if sym:
        s = s.replace(sym, " ")
    s = re.sub(rf"\b{re.escape(code)}\b", " ", s, flags=re.IGNORECASE)
    s = _NUMBER_RE.sub(" ", s)
    s = s.replace("+", " ").replace("-", " ")
    kept: list[str] = []
    for word in s.split():
        lw = word.lower().strip(".,!?:;()")
        if lw in _STRIP_WORDS:
            continue
        kept.append(word.strip(".,!?:;()"))
    return " ".join(kept).strip()


def _is_income(text: str) -> bool:
    if text.lstrip().startswith("+"):
        return True
    lowered = text.lower()
    return any(w in lowered for w in _INCOME_WORDS)


def parse(text: str, default_currency: str = DEFAULT_CURRENCY) -> Draft:
    s = text.strip()
    if not s:
        return Draft(currency=default_currency, reason="empty input")

    code = _detect_currency(s, default_currency)
    is_income = _is_income(s)
    amount = _extract_amount(s)
    desc = _extract_description(s, code)

    draft = Draft(
        currency=code,
        type="income" if is_income else "expense",
        description=desc,
        source="text",
    )
    if amount is None:
        draft.reason = "no amount found"
        return draft
    draft.amount_minor = to_minor(amount, code)
    return draft


CATEGORY_SYSTEM_PROMPT = (
    "You are a bookkeeping assistant. Given an expense or income description and "
    "amount, choose a short category name (for example Food, Transport, Utilities, "
    "Salary, Shopping). Respond with valid JSON only, in the form "
    '{"category": "..."}.'
)


async def categorize(draft: Draft, provider: Provider | None = None) -> str | None:
    if provider is None or not getattr(provider, "configured", False):
        return None
    user = draft.description or draft.reason or ""
    if not user.strip():
        return None
    try:
        raw = await provider.text(CATEGORY_SYSTEM_PROMPT, user, json_mode=True)
    except ProviderError:
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    category = data.get("category")
    if isinstance(category, str) and category.strip():
        return category.strip()
    return None
