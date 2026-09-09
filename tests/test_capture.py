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
