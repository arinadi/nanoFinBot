"""Tests for PDF and CSV report generation."""

import csv
from io import StringIO

from nanofinbot import db, reports


async def _add_active(*, amount_minor, currency, type="expense", description="", category_id=None):
    tx_id = await db.create_draft(
        amount_minor=amount_minor,
        currency=currency,
        type=type,
        description=description,
        category_id=category_id,
    )
    await db.set_status(tx_id, "active")
    return tx_id


async def test_pdf_totals(fresh_db):
    cid = await db.get_or_create_category("Food")
    await _add_active(amount_minor=10000, currency="IDR", description="lunch", category_id=cid)

    rows = await db.list_transactions(status="active")
    pdf = reports.build_pdf(rows)
    text = pdf.decode("latin-1")
    assert "Food" in text
    assert "Rp 10,000" in text


async def test_pdf_excludes_disabled(fresh_db):
    cid = await db.get_or_create_category("Food")
    await _add_active(amount_minor=10000, currency="IDR", description="lunch", category_id=cid)
    hidden = await db.create_draft(amount_minor=500000, currency="IDR", description="void", category_id=cid)
    await db.set_status(hidden, "active")
    await db.set_status(hidden, "disabled")

    rows = await db.list_transactions(status="active")
    pdf = reports.build_pdf(rows)
    text = pdf.decode("latin-1")
    assert "Rp 10,000" in text
    assert "Rp 500,000" not in text


async def test_csv_rows(fresh_db):
    cid = await db.get_or_create_category("Food")
    await _add_active(amount_minor=5000, currency="USD", description="pizza", category_id=cid)

    rows = await db.list_transactions(status="active")
    csv_bytes = reports.build_csv(rows)
    text = csv_bytes.decode("utf-8-sig")
    parsed = list(csv.reader(StringIO(text)))
    assert parsed[0] == ["date", "type", "amount", "currency", "category", "description"]
    assert parsed[1][2] == "50.00"
    assert parsed[1][3] == "USD"
    assert parsed[1][4] == "Food"
    assert parsed[1][5] == "pizza"


async def test_csv_excludes_disabled(fresh_db):
    cid = await db.get_or_create_category("Food")
    await _add_active(amount_minor=5000, currency="USD", description="pizza", category_id=cid)
    hidden = await db.create_draft(amount_minor=999, currency="USD", description="void", category_id=cid)
    await db.set_status(hidden, "active")
    await db.set_status(hidden, "disabled")

    rows = await db.list_transactions(status="active")
    csv_bytes = reports.build_csv(rows)
    text = csv_bytes.decode("utf-8-sig")
    parsed = list(csv.reader(StringIO(text)))
    assert len(parsed) == 2  # header + one row
