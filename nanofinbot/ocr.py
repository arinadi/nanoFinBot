"""OCR: turn a receipt photo into a draft via the vision provider."""

from __future__ import annotations

import asyncio
import json
from io import BytesIO

from PIL import Image

from nanofinbot.config import DEFAULT_CURRENCY
from nanofinbot.db import normalize_currency
from nanofinbot.parser import Draft, draft_from_json
from nanofinbot.provider import Provider, ProviderError

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

OCR_SYSTEM_PROMPT = (
    "You are a receipt reader. Extract the transaction from the image and respond "
    'with valid JSON only, in the form {"amount": 12.34, "currency": "USD", '
    '"type": "expense", "description": "...", "category": "..."}. '
    '"type" is either "expense" or "income". "currency" is a 3-letter ISO code. '
    'If a field cannot be read, use null. Do not invent data.'
)


def preprocess(image_bytes: bytes, max_dim: int = 768) -> bytes:
    """Downscale to a 768px grid and re-encode as JPEG (never touches disk)."""
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError("image too large")
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
    currency = normalize_currency(default_currency, "IDR")
    base = Draft(source="photo", currency=currency)
    if provider is None or not getattr(provider, "configured", False):
        base.reason = "no provider configured"
        return base

    try:
        processed = await asyncio.to_thread(preprocess, image_bytes)
    except (ValueError, OSError):
        base.reason = "could not process image"
        return base

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

    return draft_from_json(data, default_currency, "photo")
