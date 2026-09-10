"""SQLite persistence for nanoFinBot.

A single shared aiosqlite connection guarded by an asyncio.Lock. Amounts are
stored as integer minor units plus an ISO 4217 currency code (see architecture.md
section 2). The ``CURRENCIES`` map drives parsing and formatting.
"""

from __future__ import annotations

import asyncio
import calendar
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import aiosqlite

from nanofinbot.config import data_dir

CURRENCIES: dict[str, tuple[str, int]] = {
    "IDR": ("Rp", 0),
    "USD": ("$", 2),
    "EUR": ("€", 2),
    "GBP": ("£", 2),
    "JPY": ("¥", 0),
    "SGD": ("S$", 2),
    "MYR": ("RM", 2),
    "AUD": ("A$", 2),
    "THB": ("฿", 2),
    "PHP": ("₱", 2),
    "VND": ("₫", 0),
    "KRW": ("₩", 0),
    "CNY": ("¥", 2),
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount_minor INTEGER,
    currency TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    category_id INTEGER,
    source TEXT NOT NULL DEFAULT 'text',
    status TEXT NOT NULL DEFAULT 'draft',
    created_by INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS recurring (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    amount_minor INTEGER NOT NULL,
    currency TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'expense',
    category_id INTEGER,
    frequency TEXT NOT NULL,
    next_due TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);
"""

_db: aiosqlite.Connection | None = None
_lock = asyncio.Lock()
_db_path: Path | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dict(row: aiosqlite.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def get_minor_exponent(code: str) -> int:
    return CURRENCIES.get(code.upper(), ("", 0))[1]


def get_symbol(code: str) -> str:
    return CURRENCIES.get(code.upper(), ("", 0))[0]


MAX_AMOUNT_MINOR = 10 ** 12


def normalize_currency(code: str, default: str) -> str:
    normalized = str(code).upper()
    if normalized in CURRENCIES:
        return normalized
    default_norm = str(default).upper()
    if default_norm in CURRENCIES:
        return default_norm
    return "IDR"


def to_minor(amount: float, code: str) -> int:
    if not math.isfinite(amount):
        raise ValueError("amount must be finite")
    minor = int(round(amount * (10 ** get_minor_exponent(code))))
    if abs(minor) > MAX_AMOUNT_MINOR:
        raise ValueError("amount too large")
    return minor


def valid_minor(amount: float, code: str) -> int | None:
    """Return positive minor units, or None when invalid/zero/negative/too large."""
    try:
        minor = to_minor(amount, code)
    except (ValueError, OverflowError):
        return None
    return minor if minor > 0 else None


def format_amount(minor: int, code: str) -> str:
    exp = get_minor_exponent(code)
    sym = get_symbol(code)
    if exp == 0:
        return f"{sym} {minor:,}"
    units = minor / (10 ** exp)
    return f"{sym} {units:,.{exp}f}"


async def init_db(path: Path | str | None = None) -> None:
    """Open the database and create the schema if absent."""
    global _db, _db_path
    await close_db()
    if path is None:
        path = data_dir() / "nfb.db"
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    _db = await aiosqlite.connect(str(p))
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA foreign_keys=ON")
    await _db.executescript(SCHEMA)
    await _db.commit()
    _db_path = p


async def close_db() -> None:
    global _db, _db_path
    if _db is not None:
        await _db.close()
    _db = None
    _db_path = None


def _conn() -> aiosqlite.Connection:
    if _db is None:
        raise RuntimeError("database not initialized; call init_db() first")
    return _db


# --- transactions ---

async def create_draft(
    *,
    amount_minor: int | None,
    currency: str,
    type: str = "expense",
    description: str = "",
    category_id: int | None = None,
    source: str = "text",
    created_by: int | None = None,
) -> int:
    async with _lock:
        cur = await _conn().execute(
            "INSERT INTO transactions "
            "(amount_minor, currency, type, description, category_id, source, status, created_by, created_at) "
            "VALUES (?,?,?,?,?,?, 'draft', ?,?)",
            (amount_minor, currency, type, description, category_id, source, created_by, _now_iso()),
        )
        await _conn().commit()
        return cur.lastrowid


async def update_draft(
    draft_id: int,
    *,
    amount_minor: int | None,
    currency: str,
    type: str,
    description: str,
    category_id: int | None = None,
) -> bool:
    """Update a draft. Only valid while status is 'draft' (immutability)."""
    async with _lock:
        cur = await _conn().execute(
            "UPDATE transactions SET amount_minor=?, currency=?, type=?, description=?, category_id=? "
            "WHERE id=? AND status='draft'",
            (amount_minor, currency, type, description, category_id, draft_id),
        )
        await _conn().commit()
        return cur.rowcount > 0


async def get_transaction(tx_id: int) -> dict | None:
    cur = await _conn().execute(
        "SELECT t.*, c.name AS category_name FROM transactions t "
        "LEFT JOIN categories c ON t.category_id=c.id WHERE t.id=?",
        (tx_id,),
    )
    row = await cur.fetchone()
    return _dict(row) if row else None


async def set_status(tx_id: int, status: str) -> bool:
    """Allowed transitions: draft->active, active->disabled."""
    async with _lock:
        cur = await _conn().execute(
            "UPDATE transactions SET status=? WHERE id=? AND "
            "((status='draft' AND ?='active') OR (status='active' AND ?='disabled'))",
            (status, tx_id, status, status),
        )
        await _conn().commit()
        return cur.rowcount > 0


async def delete_draft(tx_id: int) -> bool:
    async with _lock:
        cur = await _conn().execute(
            "DELETE FROM transactions WHERE id=? AND status='draft'",
            (tx_id,),
        )
        await _conn().commit()
        return cur.rowcount > 0


async def list_transactions(
    *,
    status: str | None = None,
    start: str | None = None,
    end: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    q = (
        "SELECT t.*, c.name AS category_name FROM transactions t "
        "LEFT JOIN categories c ON t.category_id=c.id"
    )
    clauses: list[str] = []
    params: list = []
    if status is not None:
        clauses.append("t.status = ?")
        params.append(status)
    if start is not None:
        clauses.append("t.created_at >= ?")
        params.append(start)
    if end is not None:
        clauses.append("t.created_at < ?")
        params.append(end)
    if clauses:
        q += " WHERE " + " AND ".join(clauses)
    q += " ORDER BY t.created_at DESC, t.id DESC"
    if limit is not None:
        q += " LIMIT ?"
        params.append(limit)
    cur = await _conn().execute(q, params)
    rows = await cur.fetchall()
    return [_dict(r) for r in rows]


# --- categories ---

def _normalize_category(name: str) -> str:
    return " ".join(name.strip().split()).title() or "Uncategorized"


async def list_categories() -> list[dict]:
    cur = await _conn().execute("SELECT * FROM categories ORDER BY name")
    rows = await cur.fetchall()
    return [_dict(r) for r in rows]


async def get_or_create_category(name: str) -> int:
    normalized = _normalize_category(name)
    async with _lock:
        cur = await _conn().execute("SELECT id FROM categories WHERE lower(name)=lower(?)", (normalized,))
        row = await cur.fetchone()
        if row:
            return row["id"]
        cur = await _conn().execute("INSERT INTO categories (name, created_at) VALUES (?,?)", (normalized, _now_iso()))
        await _conn().commit()
        return cur.lastrowid


async def rename_category(category_id: int, new_name: str) -> bool:
    if not new_name or not new_name.strip():
        return False
    normalized = _normalize_category(new_name)
    async with _lock:
        dup = await _conn().execute("SELECT id FROM categories WHERE lower(name)=lower(?) AND id != ?", (normalized, category_id))
        if await dup.fetchone():
            return False
        cur = await _conn().execute("UPDATE categories SET name=? WHERE id=?", (normalized, category_id))
        await _conn().commit()
        return cur.rowcount > 0


# --- recurring ---

async def create_recurring(
    *,
    description: str,
    amount_minor: int,
    currency: str,
    type: str = "expense",
    frequency: str,
    next_due: str,
    category_id: int | None = None,
) -> int:
    async with _lock:
        cur = await _conn().execute(
            "INSERT INTO recurring (description, amount_minor, currency, type, category_id, frequency, next_due, active, created_at) "
            "VALUES (?,?,?,?,?,?,?,1,?)",
            (description, amount_minor, currency, type, category_id, frequency, next_due, _now_iso()),
        )
        await _conn().commit()
        return cur.lastrowid


async def list_recurring(active_only: bool = True) -> list[dict]:
    q = "SELECT * FROM recurring"
    params: list = []
    if active_only:
        q += " WHERE active=1"
    q += " ORDER BY next_due"
    cur = await _conn().execute(q, params)
    rows = await cur.fetchall()
    return [_dict(r) for r in rows]


async def due_recurring(today: str) -> list[dict]:
    cur = await _conn().execute(
        "SELECT * FROM recurring WHERE active=1 AND next_due <= ? ORDER BY next_due",
        (today,),
    )
    rows = await cur.fetchall()
    return [_dict(r) for r in rows]


def _add_month(d: date) -> date:
    year, month = d.year, d.month + 1
    if month > 12:
        year, month = year + 1, 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _add_year(d: date) -> date:
    day = min(d.day, calendar.monthrange(d.year + 1, d.month)[1])
    return date(d.year + 1, d.month, day)


def advance_due(next_due: str, frequency: str) -> str:
    d = date.fromisoformat(next_due)
    if frequency == "daily":
        d = date(d.year, d.month, d.day) + timedelta(days=1)
    elif frequency == "weekly":
        d = date(d.year, d.month, d.day) + timedelta(days=7)
    elif frequency == "monthly":
        d = _add_month(d)
    elif frequency == "yearly":
        d = _add_year(d)
    return d.isoformat()


async def set_next_due(recurring_id: int, next_due: str) -> None:
    async with _lock:
        await _conn().execute("UPDATE recurring SET next_due=? WHERE id=?", (next_due, recurring_id))
        await _conn().commit()
