"""Tests for the SQLite schema and transaction repository."""

from nanofinbot import db


async def test_schema(fresh_db):
    conn = db._conn()
    cur = await conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    names = {r["name"] for r in await cur.fetchall()}
    assert {"transactions", "categories", "recurring"} <= names


async def test_roundtrip(fresh_db):
    tx_id = await db.create_draft(amount_minor=5000, currency="USD", type="expense", description="pizza")
    rows = await db.list_transactions(status="draft")
    assert len(rows) == 1
    r = rows[0]
    assert r["id"] == tx_id
    assert r["amount_minor"] == 5000
    assert r["currency"] == "USD"
    assert r["type"] == "expense"
    assert r["description"] == "pizza"
    assert r["status"] == "draft"


async def test_immutable(fresh_db):
    tx_id = await db.create_draft(amount_minor=5000, currency="USD", type="expense", description="pizza")
    assert await db.set_status(tx_id, "active")

    updated = await db.update_draft(tx_id, amount_minor=999, currency="USD", type="expense", description="x")
    assert updated is False

    row = await db.get_transaction(tx_id)
    assert row["amount_minor"] == 5000
    assert row["status"] == "active"


async def test_disabled_transition(fresh_db):
    tx_id = await db.create_draft(amount_minor=100, currency="IDR", type="expense", description="x")
    await db.set_status(tx_id, "active")
    assert await db.set_status(tx_id, "disabled")
    row = await db.get_transaction(tx_id)
    assert row["status"] == "disabled"


async def test_amount_formatting():
    assert db.to_minor(50, "USD") == 5000
    assert db.to_minor(50000, "IDR") == 50000
    assert db.format_amount(12500, "IDR") == "Rp 12,500"
    assert db.format_amount(5000, "USD") == "$ 50.00"
