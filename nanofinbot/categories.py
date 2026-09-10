"""Category management UI: list and rename."""

from __future__ import annotations

from nanofinbot import db


async def on_categories(bot, chat_id: int) -> None:
    cats = await db.list_categories()
    if not cats:
        await bot.send_message(chat_id, "No categories yet.")
        return
    await bot.send_message(chat_id, "\n".join(f"- {c['id']}: {c['name']}" for c in cats))


async def on_rename(bot, chat_id: int, text: str) -> None:
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        await bot.send_message(chat_id, "Usage: /rename <id> <new name>")
        return
    try:
        category_id = int(parts[1])
    except ValueError:
        await bot.send_message(chat_id, "Category id must be a number.")
        return
    ok = await db.rename_category(category_id, parts[2])
    await bot.send_message(chat_id, "Renamed." if ok else "Rename failed (duplicate or empty name).")
