"""Recurring items: definition and due reminders."""

from __future__ import annotations

from datetime import date

from nanofinbot import db
from nanofinbot.config import Config


async def add_item(
    *,
    description: str,
    amount_minor: int,
    currency: str,
    type: str = "expense",
    frequency: str,
    next_due: str,
) -> int:
    return await db.create_recurring(
        description=description,
        amount_minor=amount_minor,
        currency=currency,
        type=type,
        frequency=frequency,
        next_due=next_due,
    )


async def list_items(bot, chat_id: int) -> None:
    items = await db.list_recurring(active_only=True)
    if not items:
        await bot.send_message(chat_id, "No recurring items.")
        return
    lines = ["Recurring items:"]
    for item in items:
        lines.append(
            f"- {item['description']} "
            f"{db.format_amount(item['amount_minor'], item['currency'])} "
            f"every {item['frequency']} (next {item['next_due']})"
        )
    await bot.send_message(chat_id, "\n".join(lines))


async def check_due(bot, cfg: Config, today: str | None = None) -> int:
    """Send reminders for due items and advance their next_due. Reminders only."""
    if cfg.group_id is None:
        return 0
    today = today or date.today().isoformat()
    due = await db.due_recurring(today)
    sent = 0
    for item in due:
        await bot.send_message(
            cfg.group_id,
            f"Reminder: {item['description']} "
            f"({db.format_amount(item['amount_minor'], item['currency'])}) is due.",
        )
        await db.set_next_due(item["id"], db.advance_due(item["next_due"], item["frequency"]))
        sent += 1
    return sent
