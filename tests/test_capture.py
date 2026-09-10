"""Tests for the capture flow: save, edit, cancel."""

from nanofinbot import capture, db
from nanofinbot.config import Config


def cfg() -> Config:
    return Config(telegram_token="x", group_id=None, default_currency="USD")


async def _draft_id() -> int:
    return (await db.list_transactions(status="draft"))[0]["id"]


async def test_draft_shown(fresh_db, fake_bot):
    await capture.on_text(fake_bot, cfg(), None, chat_id=1, user_id=1, text="spend 50 pizza")
    assert len(fake_bot.sent) == 1
    kb = fake_bot.sent[0]["reply_markup"]
    buttons = [b for row in kb.inline_keyboard for b in row]
    assert {b.text for b in buttons} == {"Save", "Edit", "Cancel"}
    assert len(await db.list_transactions(status="draft")) == 1


class ParseProvider:
    configured = True

    def __init__(self, content):
        self.content = content

    async def text(self, system, user, json_mode=False):
        return self.content


async def test_text_uses_llm(fresh_db, fake_bot):
    provider = ParseProvider(
        '{"amount": 30, "currency": "USD", "type": "expense", '
        '"description": "Lunch", "category": "Food"}'
    )
    await capture.on_text(fake_bot, cfg(), provider, 1, 1, "lunch at cafe")
    row = (await db.list_transactions(status="draft"))[0]
    assert row["amount_minor"] == 3000
    assert row["description"] == "Lunch"
    assert row["category_name"] == "Food"


async def test_text_falls_back_to_rules(fresh_db, fake_bot):
    provider = ParseProvider("this is not json")
    await capture.on_text(fake_bot, cfg(), provider, 1, 1, "spend 50 pizza")
    row = (await db.list_transactions(status="draft"))[0]
    assert row["amount_minor"] == 5000
    assert row["description"] == "pizza"


async def test_debug_on_sends_raw(fresh_db, fake_bot):
    c = cfg()
    c.debug = True
    provider = ParseProvider(
        '{"amount": 30, "currency": "USD", "type": "expense", '
        '"description": "Lunch", "category": "Food"}'
    )
    await capture.on_text(fake_bot, c, provider, 1, 1, "lunch at cafe")
    assert any("[debug] llm_parse" in m["text"] for m in fake_bot.sent)
    assert any('"amount": 30' in m["text"] for m in fake_bot.sent)


async def test_debug_off_sends_no_raw(fresh_db, fake_bot):
    c = cfg()
    c.debug = False
    provider = ParseProvider(
        '{"amount": 30, "currency": "USD", "type": "expense", '
        '"description": "Lunch", "category": "Food"}'
    )
    await capture.on_text(fake_bot, c, provider, 1, 1, "lunch at cafe")
    assert not any("[debug]" in m["text"] for m in fake_bot.sent)


async def test_save(fresh_db, fake_bot):
    await capture.on_text(fake_bot, cfg(), None, 1, 1, "spend 50 pizza")
    draft_id = await _draft_id()
    await capture.on_save(fake_bot, chat_id=1, draft_id=draft_id)
    row = await db.get_transaction(draft_id)
    assert row["status"] == "active"
    assert any("Saved" in m["text"] for m in fake_bot.sent)


async def test_active_immutable(fresh_db, fake_bot):
    await capture.on_text(fake_bot, cfg(), None, 1, 1, "spend 50 pizza")
    draft_id = await _draft_id()
    await capture.on_save(fake_bot, 1, draft_id)

    updated = await db.update_draft(
        draft_id, amount_minor=1, currency="USD", type="expense", description="x"
    )
    assert updated is False
    assert (await db.get_transaction(draft_id))["amount_minor"] == 5000


async def test_edit(fresh_db, fake_bot):
    await capture.on_text(fake_bot, cfg(), None, 1, 1, "spend 50 pizza")
    draft_id = await _draft_id()

    await capture.on_edit(fake_bot, chat_id=1, user_id=1, draft_id=draft_id)
    await capture.on_text(fake_bot, cfg(), None, 1, 1, "spend 30 lunch")

    row = await db.get_transaction(draft_id)
    assert row["amount_minor"] == 3000
    assert row["description"] == "lunch"
    assert row["status"] == "draft"
    assert fake_bot.sent[-1]["reply_markup"] is not None


async def test_edit_active_refused(fresh_db, fake_bot):
    await capture.on_text(fake_bot, cfg(), None, 1, 1, "spend 50 pizza")
    draft_id = await _draft_id()
    await capture.on_save(fake_bot, 1, draft_id)

    await capture.on_edit(fake_bot, chat_id=1, user_id=1, draft_id=draft_id)
    assert any("no longer be edited" in m["text"] for m in fake_bot.sent)


async def test_cancel(fresh_db, fake_bot):
    await capture.on_text(fake_bot, cfg(), None, 1, 1, "spend 50 pizza")
    draft_id = await _draft_id()
    await capture.on_cancel(fake_bot, chat_id=1, draft_id=draft_id)
    assert await db.get_transaction(draft_id) is None
    assert any("discarded" in m["text"] for m in fake_bot.sent)


async def test_cancel_not_listed(fresh_db, fake_bot):
    await capture.on_text(fake_bot, cfg(), None, 1, 1, "spend 50 pizza")
    draft_id = await _draft_id()
    await capture.on_cancel(fake_bot, 1, draft_id)
    assert await db.list_transactions() == []


async def test_save_zero_rejected(fresh_db, fake_bot):
    tx = await db.create_draft(amount_minor=0, currency="USD", type="expense", description="x")
    await capture.on_save(fake_bot, chat_id=1, draft_id=tx)
    assert (await db.get_transaction(tx))["status"] == "draft"
    assert any("positive" in m["text"] for m in fake_bot.sent)


async def test_resume_pending(fresh_db, fake_bot):
    await db.create_draft(amount_minor=100, currency="IDR", type="expense", description="first", created_by=7)
    await db.create_draft(amount_minor=200, currency="IDR", type="expense", description="second", created_by=7)

    await capture.resume_pending(fake_bot, chat_id=9)

    assert len(fake_bot.sent) == 1
    assert "first" in fake_bot.sent[0]["text"]
