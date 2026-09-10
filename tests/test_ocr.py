"""Tests for OCR photo-to-draft."""

from io import BytesIO

from PIL import Image

from nanofinbot import ocr
from nanofinbot.ocr import photo_to_draft


def make_image() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (120, 120), "white").save(buf, format="JPEG")
    return buf.getvalue()


class FakeVisionProvider:
    def __init__(self, content, configured=True):
        self.content = content
        self.configured = configured

    async def vision(self, system, image_bytes, json_mode=False):
        return self.content


async def test_photo_to_draft():
    provider = FakeVisionProvider(
        '{"amount": 50, "currency": "USD", "type": "expense", '
        '"description": "Lunch", "category": "Food"}'
    )
    d = await photo_to_draft(make_image(), "IDR", provider=provider)
    assert d.amount_minor == 5000
    assert d.currency == "USD"
    assert d.type == "expense"
    assert d.description == "Lunch"
    assert d.category == "Food"
    assert d.source == "photo"


async def test_bad_json():
    provider = FakeVisionProvider("this is not json")
    d = await photo_to_draft(make_image(), "IDR", provider=provider)
    assert d.amount_minor is None
    assert d.reason


async def test_no_image_persisted(tmp_path):
    provider = FakeVisionProvider(
        '{"amount": 10, "currency": "IDR", "type": "expense", "description": "x"}'
    )
    await photo_to_draft(make_image(), "IDR", provider=provider)
    assert list(tmp_path.rglob("*")) == []


async def test_unknown_currency_falls_back():
    provider = FakeVisionProvider(
        '{"amount": 10, "currency": "XYZ", "type": "expense", "description": "x"}'
    )
    d = await photo_to_draft(make_image(), "IDR", provider=provider)
    assert d.currency == "IDR"
    assert d.amount_minor == 10


async def test_negative_amount_rejected():
    provider = FakeVisionProvider(
        '{"amount": -5, "currency": "USD", "type": "expense", "description": "x"}'
    )
    d = await photo_to_draft(make_image(), "USD", provider=provider)
    assert d.amount_minor is None


async def test_oversized_image_rejected():
    provider = FakeVisionProvider('{"amount": 1, "currency": "USD"}')
    huge = b"\x00" * (ocr.MAX_IMAGE_BYTES + 1)
    d = await photo_to_draft(huge, "USD", provider=provider)
    assert d.amount_minor is None
    assert d.reason == "could not process image"
