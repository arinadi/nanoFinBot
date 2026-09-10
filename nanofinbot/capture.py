"""Capture flow: draft queue, save/edit/cancel, disable, and bulk batches.

These functions are the handlers' shared logic. They talk to the bot through a
duck-typed ``bot`` (real aiogram ``Bot`` or a test double) with ``send_message``,
``answer_document`` and ``answer_callback_query`` methods.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from nanofinbot import db
from nanofinbot.config import Config
from nanofinbot.ocr import photo_to_draft
from nanofinbot.parser import Draft, categorize, llm_parse, parse
from nanofinbot.provider import Provider

_editing: dict[int, int] = {}
_queue: dict[int, list[int]] = {}
_batch_active: set[int] = set()


def _draft_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Save", callback_data=f"save:{draft_id}")],
            [
                InlineKeyboardButton(text="Edit", callback_data=f"edit:{draft_id}"),
                InlineKeyboardButton(text="Cancel", callback_data=f"cancel:{draft_id}"),
            ],
        ]
    )


def summarize_row(row: dict) -> str:
    lines = ["Draft:"]
    if row["amount_minor"] is not None:
        lines.append(f"Amount: {db.format_amount(row['amount_minor'], row['currency'])}")
    else:
        lines.append("Amount: (none)")
    lines.append(f"Type: {row['type']}")
    if row.get("category_name"):
        lines.append(f"Category: {row['category_name']}")
    if row.get("description"):
        lines.append(f"Description: {row['description']}")
    return "\n".join(lines)


async def _resolve_category_id(draft: Draft) -> int | None:
    if draft.category:
        return await db.get_or_create_category(draft.category)
    return None


async def _create_draft_only(
    cfg: Config, provider, user_id: int, draft: Draft, debug_log: list | None = None
) -> int:
    if draft.category is None and provider is not None and getattr(provider, "configured", False):
        draft.category = await categorize(draft, provider, debug_log)

    category_id = await _resolve_category_id(draft)
    return await db.create_draft(
        amount_minor=draft.amount_minor,
        currency=draft.currency,
        type=draft.type,
        description=draft.description,
        category_id=category_id,
        source=draft.source,
        created_by=user_id,
    )


async def _present_draft(bot, chat_id: int, tx_id: int) -> None:
    row = await db.get_transaction(tx_id)
    await bot.send_message(chat_id, summarize_row(row), reply_markup=_draft_keyboard(tx_id))


async def _debug_dump(bot, cfg: Config, chat_id: int, entries: list) -> None:
    if not cfg.debug or not entries:
        return
    for kind, raw in entries:
        target = cfg.provider if kind != "vision" else (cfg.image_provider or cfg.provider)
        await bot.send_message(
            chat_id,
            f"[debug] {kind}\n{target.base_url} | {target.model}\nraw: {(raw or '')[:3500]}",
        )


async def _present_next(bot, chat_id: int, user_id: int) -> None:
    q = _queue.get(user_id)
    while q:
        tx_id = q.pop(0)
        row = await db.get_transaction(tx_id)
        if row is not None and row["status"] == "draft":
            await _present_draft(bot, chat_id, tx_id)
            return
    _queue.pop(user_id, None)
    if user_id in _batch_active:
        _batch_active.discard(user_id)
        await bot.send_message(chat_id, "All queued items processed.")


async def _parse_text(cfg: Config, provider, text: str, debug_log: list | None = None) -> Draft:
    """LLM-first text parsing with rules fallback (offline-safe)."""
    if provider is not None and getattr(provider, "configured", False):
        draft = await llm_parse(text, cfg.default_currency, provider, debug_log)
        if draft.amount_minor is not None:
            return draft
    return parse(text, cfg.default_currency)


async def on_text(bot, cfg: Config, provider, chat_id: int, user_id: int, text: str) -> None:
    if user_id in _editing:
        draft_id = _editing.pop(user_id)
        await _apply_edit(bot, cfg, provider, chat_id, user_id, draft_id, text)
        return

    debug_log: list = []
    draft = await _parse_text(cfg, provider, text, debug_log)
    if draft.amount_minor is None:
        await _debug_dump(bot, cfg, chat_id, debug_log)
        await bot.send_message(
            chat_id,
            "I couldn't parse that. Try something like `spend 50 pizza` or `+3500 salary`.",
        )
        return
    tx_id = await _create_draft_only(cfg, provider, user_id, draft, debug_log)
    await _debug_dump(bot, cfg, chat_id, debug_log)
    await _present_draft(bot, chat_id, tx_id)


async def on_photo(bot, cfg: Config, provider, chat_id: int, user_id: int, image_bytes: bytes) -> None:
    debug_log: list = []
    draft = await photo_to_draft(image_bytes, cfg.default_currency, provider, debug_log)
    tx_id = await _create_draft_only(cfg, provider, user_id, draft, debug_log)
    await _debug_dump(bot, cfg, chat_id, debug_log)
    await _present_draft(bot, chat_id, tx_id)


async def on_photos(bot, cfg: Config, provider, chat_id: int, user_id: int, images: list[bytes]) -> None:
    """Create one draft per photo, present the first, queue the rest."""
    ids = []
    debug_log: list = []
    for image in images:
        draft = await photo_to_draft(image, cfg.default_currency, provider, debug_log)
        ids.append(await _create_draft_only(cfg, provider, user_id, draft, debug_log))
    if not ids:
        return
    _queue[user_id] = ids[1:]
    _batch_active.add(user_id)
    await _debug_dump(bot, cfg, chat_id, debug_log)
    await _present_draft(bot, chat_id, ids[0])


async def on_save(bot, chat_id: int, draft_id: int) -> None:
    row = await db.get_transaction(draft_id)
    if row is None or row["status"] != "draft":
        return
    if row["amount_minor"] is None or row["amount_minor"] <= 0:
        await bot.send_message(chat_id, "Please set a positive amount first (use Edit).")
        return
    if await db.set_status(draft_id, "active"):
        await bot.send_message(
            chat_id,
            f"Saved: {db.format_amount(row['amount_minor'], row['currency'])} {row['description']}".strip(),
        )
    _clear_editing(row["created_by"], draft_id)
    await _present_next(bot, chat_id, row["created_by"])


async def on_edit(bot, chat_id: int, user_id: int, draft_id: int) -> None:
    row = await db.get_transaction(draft_id)
    if row is None or row["status"] != "draft":
        await bot.send_message(chat_id, "This item can no longer be edited.")
        return
    _editing[user_id] = draft_id
    await bot.send_message(
        chat_id,
        "Send a new entry to replace this draft, e.g. `spend 30 lunch`.",
    )


async def _apply_edit(bot, cfg: Config, provider, chat_id: int, user_id: int, draft_id: int, text: str) -> None:
    row = await db.get_transaction(draft_id)
    if row is None or row["status"] != "draft":
        await bot.send_message(chat_id, "This item can no longer be edited.")
        return

    debug_log: list = []
    draft = await _parse_text(cfg, provider, text, debug_log)
    if draft.amount_minor is None:
        _editing[user_id] = draft_id
        await _debug_dump(bot, cfg, chat_id, debug_log)
        await bot.send_message(chat_id, "I couldn't parse that edit. Try again.")
        return

    category_id = await _resolve_category_id(draft)
    await db.update_draft(
        draft_id,
        amount_minor=draft.amount_minor,
        currency=draft.currency,
        type=draft.type,
        description=draft.description,
        category_id=category_id,
    )
    updated = await db.get_transaction(draft_id)
    await bot.send_message(chat_id, summarize_row(updated), reply_markup=_draft_keyboard(draft_id))


async def on_cancel(bot, chat_id: int, draft_id: int) -> None:
    row = await db.get_transaction(draft_id)
    if row is None or row["status"] != "draft":
        return
    if await db.delete_draft(draft_id):
        await bot.send_message(chat_id, "Draft discarded.")
        _clear_editing(row["created_by"], draft_id)
        await _present_next(bot, chat_id, row["created_by"])


def _clear_editing(user_id: int | None, draft_id: int) -> None:
    if user_id is not None and _editing.get(user_id) == draft_id:
        _editing.pop(user_id, None)


async def resume_pending(bot, chat_id: int) -> None:
    """Re-present the oldest pending draft on restart (architecture risk 4)."""
    drafts = await db.list_transactions(status="draft")
    if not drafts:
        return
    drafts.sort(key=lambda r: r["id"])
    first, rest = drafts[0], drafts[1:]
    if first["created_by"] is not None:
        _queue.setdefault(first["created_by"], []).extend(r["id"] for r in rest)
    await _present_draft(bot, chat_id, first["id"])


async def on_disable(bot, chat_id: int, tx_id: int) -> None:
    row = await db.get_transaction(tx_id)
    if row is None or row["status"] != "active":
        return
    if await db.set_status(tx_id, "disabled"):
        await bot.send_message(chat_id, "Transaction disabled.")


def _active_summary(row: dict) -> str:
    lines = [
        db.format_amount(row["amount_minor"], row["currency"]),
        row["type"],
    ]
    if row.get("category_name"):
        lines.append(row["category_name"])
    if row.get("description"):
        lines.append(row["description"])
    return " — ".join(lines)


async def on_list(bot, chat_id: int, limit: int = 10) -> None:
    rows = await db.list_transactions(status="active", limit=limit)
    if not rows:
        await bot.send_message(chat_id, "No saved transactions yet.")
        return
    for row in rows:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Disable", callback_data=f"disable:{row['id']}")]
            ]
        )
        await bot.send_message(chat_id, _active_summary(row), reply_markup=kb)
