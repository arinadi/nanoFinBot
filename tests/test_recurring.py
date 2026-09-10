"""Tests for recurring items and due reminders."""

import pytest

from nanofinbot import db, recurring
from nanofinbot.config import Config


async def test_add_list(fresh_db, fake_bot):
    await recurring.add_item(
        description="Rent",
        amount_minor=1000000,
        currency="IDR",
        frequency="monthly",
        next_due="2026-09-01",
    )
    await recurring.list_items(fake_bot, chat_id=1)
    assert any("Rent" in m["text"] for m in fake_bot.sent)
    items = await db.list_recurring()
    assert len(items) == 1


async def test_due_reminder(fresh_db, fake_bot):
    await recurring.add_item(
        description="Rent",
        amount_minor=1000000,
        currency="IDR",
        frequency="monthly",
        next_due="2026-01-01",
    )
    cfg = Config(telegram_token="x", group_id=5)
    sent = await recurring.check_due(fake_bot, cfg, today="2026-01-15")
    assert sent == 1
    assert any("Rent" in m["text"] for m in fake_bot.sent)

    items = await db.list_recurring()
    assert items[0]["next_due"] == "2026-02-01"


async def test_no_auto_entry(fresh_db, fake_bot):
    await recurring.add_item(
        description="Rent",
        amount_minor=1000000,
        currency="IDR",
        frequency="monthly",
        next_due="2026-01-01",
    )
    cfg = Config(telegram_token="x", group_id=5)
    await recurring.check_due(fake_bot, cfg, today="2026-01-15")
    assert await db.list_transactions() == []


class RaisingBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, **kwargs):
        raise RuntimeError("send failed")


async def test_advance_before_send(fresh_db):
    await recurring.add_item(
        description="Rent",
        amount_minor=1000000,
        currency="IDR",
        frequency="monthly",
        next_due="2026-01-01",
    )
    cfg = Config(telegram_token="x", group_id=5)
    with pytest.raises(RuntimeError):
        await recurring.check_due(RaisingBot(), cfg, today="2026-01-15")

    items = await db.list_recurring()
    assert items[0]["next_due"] == "2026-02-01"
