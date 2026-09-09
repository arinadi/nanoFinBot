"""Tests for OCR photo-to-draft."""

from io import BytesIO

from PIL import Image

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
