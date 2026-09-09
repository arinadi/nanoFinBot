# aiosqlite 0.20.x — reference

Async SQLite. Pin 0.20.x. One connection shared via a module-level handle.

```python
import aiosqlite

db = await aiosqlite.connect(path)
db.row_factory = aiosqlite.Row            # rows act like dicts
await db.execute("PRAGMA journal_mode=WAL")
await db.execute("CREATE TABLE IF NOT EXISTS ...")
await db.commit()

cur = await db.execute("SELECT * FROM transactions WHERE id=?", (id_,))
row = await cur.fetchone()                # aiosqlite.Row or None
rows = await cur.fetchall()
```

**Schema** (from `architecture.md` §2): `transactions`, `categories`, `recurring`.
Amounts are INTEGER minor units + ISO currency. Transaction `status` ∈ draft/active/disabled.

Notes:
- `execute` is auto-committing in aiosqlite for non-SELECT unless a transaction is
  explicit; still call `commit()` after writes for safety.
- WAL mode (set once at connect) survives abrupt shutdown better — see risk chain 5.
- Keep a single shared connection to avoid SQLite "database is locked"; guard writes with
  an `asyncio.Lock`.
