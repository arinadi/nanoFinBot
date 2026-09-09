"""Tests for category auto-create and rename."""

from nanofinbot import db


async def test_auto_create(fresh_db):
    cid = await db.get_or_create_category("Food")
    assert cid is not None
    cats = await db.list_categories()
    assert any(c["id"] == cid and c["name"] == "Food" for c in cats)


async def test_no_duplicate(fresh_db):
    c1 = await db.get_or_create_category("Food")
    c2 = await db.get_or_create_category("food")
    assert c1 == c2
    assert len(await db.list_categories()) == 1


async def test_rename(fresh_db):
    cid = await db.get_or_create_category("Food")
    tx_id = await db.create_draft(amount_minor=1000, currency="IDR", description="lunch", category_id=cid)
    await db.set_status(tx_id, "active")

    assert await db.rename_category(cid, "Groceries")
    row = await db.get_transaction(tx_id)
    assert row["category_name"] == "Groceries"


async def test_rename_duplicate_rejected(fresh_db):
    await db.get_or_create_category("Food")
    transport = await db.get_or_create_category("Transport")
    assert await db.rename_category(transport, "Food") is False


async def test_rename_empty_rejected(fresh_db):
    cid = await db.get_or_create_category("Food")
    assert await db.rename_category(cid, "   ") is False
