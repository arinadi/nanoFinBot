"""Tests for disabling saved transactions."""

from nanofinbot import capture, db


async def test_disable(fresh_db, fake_bot):
    tx = await db.create_draft(amount_minor=1000, currency="IDR", description="x")
    await db.set_status(tx, "active")

    await capture.on_disable(fake_bot, chat_id=1, tx_id=tx)

    assert (await db.get_transaction(tx))["status"] == "disabled"
    active = await db.list_transactions(status="active")
    assert all(r["id"] != tx for r in active)
    assert any("disabled" in m["text"] for m in fake_bot.sent)


async def test_no_edit_delete(fresh_db):
    tx = await db.create_draft(amount_minor=1000, currency="IDR", description="x")
    await db.set_status(tx, "active")

    assert not await db.update_draft(
        tx, amount_minor=1, currency="IDR", type="expense", description="y"
    )
    assert not await db.delete_draft(tx)
    assert (await db.get_transaction(tx))["status"] == "active"
