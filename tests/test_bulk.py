"""Tests for the bulk photo queue."""

from io import BytesIO

from PIL import Image

from nanofinbot import capture, db
from nanofinbot.config import Config


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

    async def text(self, system, user, json_mode=False):
        return '{"category": "Food"}'


def cfg() -> Config:
    return Config(telegram_token="x", group_id=None, default_currency="IDR")


async def test_queue_order(fresh_db, fake_bot):
    provider = FakeVisionProvider(
        '{"amount": 10, "currency": "IDR", "type": "expense", "description": "item"}'
    )
    images = [make_image() for _ in range(3)]
    await capture.on_photos(fake_bot, cfg(), provider, chat_id=1, user_id=1, images=images)

    # Only the first draft is presented immediately.
    assert len(fake_bot.sent) == 1
    drafts = await db.list_transactions(status="draft")
    assert len(drafts) == 3


async def test_queue_done(fresh_db, fake_bot):
    provider = FakeVisionProvider(
        '{"amount": 10, "currency": "IDR", "type": "expense", "description": "item"}'
    )
    images = [make_image() for _ in range(2)]
    await capture.on_photos(fake_bot, cfg(), provider, chat_id=1, user_id=1, images=images)

    drafts = await db.list_transactions(status="draft")
    ids = sorted(r["id"] for r in drafts)

    await capture.on_save(fake_bot, chat_id=1, draft_id=ids[0])
    await capture.on_save(fake_bot, chat_id=1, draft_id=ids[1])

    assert any("queued items processed" in m["text"] for m in fake_bot.sent)
    assert await db.list_transactions(status="draft") == []
