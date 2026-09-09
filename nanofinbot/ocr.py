"""OCR: turn a receipt photo into a draft via the vision provider."""

from __future__ import annotations

import json
from io import BytesIO

from PIL import Image

from nanofinbot.config import DEFAULT_CURRENCY
from nanofinbot.db import to_minor
from nanofinbot.parser import Draft
from nanofinbot.provider import Provider, ProviderError

OCR_SYSTEM_PROMPT = (
    "You are a receipt reader. Extract the transaction from the image and respond "
    'with valid JSON only, in the form {"amount": 12.34, "currency": "USD", '
    '"type": "expense", "description": "...", "category": "..."}. '
    '"type" is either "expense" or "income". "currency" is a 3-letter ISO code. '
    'If a field cannot be read, use null. Do not invent data.'
)


def preprocess(image_bytes: bytes, max_dim: int = 768) -> bytes:
    """Downscale to a 768px grid and re-encode as JPEG (never touches disk)."""
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((max_dim, max_dim))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


async def photo_to_draft(
    image_bytes: bytes,
    default_currency: str = DEFAULT_CURRENCY,
    provider: Provider | None = None,
) -> Draft:
    base = Draft(source="photo", currency=default_currency)
    if provider is None or not getattr(provider, "configured", False):
        base.reason = "no provider configured"
        return base

    processed = preprocess(image_bytes)
    try:
        raw = await provider.vision(OCR_SYSTEM_PROMPT, processed, json_mode=True)
    except ProviderError:
        base.reason = "provider error"
        return base

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        base.reason = "invalid json from provider"
        return base

    currency = data.get("currency") or default_currency
    if not isinstance(currency, str):
        currency = default_currency

    amount_minor = None
    try:
        amount_float = float(data.get("amount"))
    except (TypeError, ValueError):
        amount_float = None
    if amount_float is not None:
        amount_minor = to_minor(amount_float, currency)

    dtype = data.get("type")
    if dtype not in ("income", "expense"):
        dtype = "expense"

    description = data.get("description")
    if not isinstance(description, str):
        description = ""
    category = data.get("category")
    if not isinstance(category, str):
        category = None

    return Draft(
        amount_minor=amount_minor,
        currency=currency,
        type=dtype,
        description=description.strip(),
        category=category,
        source="photo",
    )
