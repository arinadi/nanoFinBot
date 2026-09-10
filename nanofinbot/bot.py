"""aiogram bot: startup status, long polling, and message/callback routing."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from nanofinbot import capture, categories, db, recurring, reports, settings
from nanofinbot.config import Config, save_config
from nanofinbot.provider import Provider
from nanofinbot.security import AuthMiddleware

_settings_state: dict[int, str] = {}
_media_pending: dict[str, list[bytes]] = {}
_media_tasks: dict[str, asyncio.Task] = {}

RECURRING_FREQUENCIES = ("daily", "weekly", "monthly", "yearly")


async def startup(bot: Bot, cfg: Config) -> None:
    """Send a ready message, then report provider status, to the configured group."""
    if cfg.group_id is None:
        return
    await bot.send_message(cfg.group_id, "nanoFinBot ready")
    await bot.send_message(cfg.group_id, settings.provider_status_text(cfg))


def _current_month_range() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        nxt = now.replace(year=now.year + 1, month=1, day=1)
    else:
        nxt = now.replace(month=now.month + 1, day=1)
    return start.isoformat(), nxt.isoformat()


def build_dispatcher(bot: Bot, cfg: Config) -> Dispatcher:
    dp = Dispatcher()
    dp.update.outer_middleware(AuthMiddleware(cfg))
    provider = Provider.from_config(cfg)

    @dp.message(CommandStart())
    async def cmd_start(msg: Message) -> None:
        await msg.answer("Hi! Send a photo or text like `spend 50 pizza`.")

    @dp.message(Command("chatid", "id"))
    async def cmd_chatid(msg: Message) -> None:
        await msg.answer(f"Chat id: {msg.chat.id}")

    @dp.message(Command("list"))
    async def cmd_list(msg: Message) -> None:
        await capture.on_list(bot, msg.chat.id)

    @dp.message(Command("report"))
    async def cmd_report(msg: Message) -> None:
        start, end = _current_month_range()
        rows = await db.list_transactions(status="active", start=start, end=end)
        pdf = await asyncio.to_thread(reports.build_pdf, rows)
        await msg.answer_document(BufferedInputFile(pdf, filename="report.pdf"))

    @dp.message(Command("export"))
    async def cmd_export(msg: Message) -> None:
        start, end = _current_month_range()
        rows = await db.list_transactions(status="active", start=start, end=end)
        csv_bytes = await asyncio.to_thread(reports.build_csv, rows)
        await msg.answer_document(BufferedInputFile(csv_bytes, filename="export.csv"))

    @dp.message(Command("categories"))
    async def cmd_categories(msg: Message) -> None:
        await categories.on_categories(bot, msg.chat.id)

    @dp.message(Command("rename"))
    async def cmd_rename(msg: Message) -> None:
        await categories.on_rename(bot, msg.chat.id, msg.text)

    @dp.message(Command("recurring"))
    async def cmd_recurring(msg: Message) -> None:
        args = msg.text.split()[1:]
        if args and args[0] == "add":
            await _recurring_add(msg, cfg, args[1:])
            return
        await recurring.list_items(bot, msg.chat.id)

    @dp.message(Command("settings"))
    async def cmd_settings(msg: Message) -> None:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Set text provider", callback_data="setprovider:text")],
                [InlineKeyboardButton(text="Set image provider", callback_data="setprovider:image")],
                [InlineKeyboardButton(text="Clear image provider", callback_data="clearimage")],
            ]
        )
        await msg.answer(settings.settings_text(cfg), reply_markup=kb)

    @dp.message(F.photo)
    async def on_photo_msg(msg: Message) -> None:
        if msg.from_user is None:
            return
        photo = msg.photo[-1]
        data = await bot.download(photo)
        image_bytes = data.read() if data is not None else b""
        group = msg.media_group_id
        if group is None:
            await capture.on_photo(bot, cfg, provider, msg.chat.id, msg.from_user.id, image_bytes)
            return
        _media_pending.setdefault(group, []).append(image_bytes)
        task = _media_tasks.get(group)
        if task is not None:
            task.cancel()
        _media_tasks[group] = asyncio.create_task(
            _flush_media(bot, cfg, provider, msg.chat.id, msg.from_user.id, group)
        )

    @dp.message(F.text)
    async def on_text_msg(msg: Message) -> None:
        if msg.from_user is None:
            return
        user_id = msg.from_user.id
        if user_id in _settings_state:
            target = _settings_state.pop(user_id)
            parts = msg.text.split()
            if len(parts) >= 2:
                base_url, model = parts[0], parts[1]
                key = parts[2] if len(parts) > 2 else ""
                if target == "text":
                    settings.set_text_provider(cfg, base_url, model, key)
                else:
                    settings.set_image_provider(cfg, base_url, model, key)
                save_config(cfg)
                await msg.answer("Provider updated.")
            else:
                await msg.answer("Format: base_url model api_key")
            return
        await capture.on_text(bot, cfg, provider, msg.chat.id, user_id, msg.text)

    @dp.callback_query()
    async def on_callback(cq: CallbackQuery) -> None:
        if cq.message is None or cq.from_user is None:
            await cq.answer()
            return
        await cq.answer()
        data = cq.data
        chat_id = cq.message.chat.id
        if data == "clearimage":
            settings.clear_image_provider(cfg)
            save_config(cfg)
            await bot.send_message(chat_id, "Image provider cleared; vision now falls back to the text provider.")
            return
        if data.startswith("setprovider:"):
            _settings_state[cq.from_user.id] = data.split(":", 1)[1]
            await bot.send_message(chat_id, "Send `base_url model api_key`.")
            return
        if data.startswith("save:"):
            await capture.on_save(bot, chat_id, int(data.split(":", 1)[1]))
        elif data.startswith("edit:"):
            await capture.on_edit(bot, chat_id, cq.from_user.id, int(data.split(":", 1)[1]))
        elif data.startswith("cancel:"):
            await capture.on_cancel(bot, chat_id, int(data.split(":", 1)[1]))
        elif data.startswith("disable:"):
            await capture.on_disable(bot, chat_id, int(data.split(":", 1)[1]))

    return dp


async def _flush_media(bot: Bot, cfg: Config, provider, chat_id: int, user_id: int, group: str) -> None:
    await asyncio.sleep(1.0)
    images = _media_pending.pop(group, [])
    _media_tasks.pop(group, None)
    if images:
        await capture.on_photos(bot, cfg, provider, chat_id, user_id, images)


async def _recurring_add(msg: Message, cfg: Config, rest: list[str]) -> None:
    if len(rest) < 5:
        await msg.answer("Usage: /recurring add <description> <amount> <currency> <frequency> <next_due> [expense|income]")
        return
    description = rest[0]
    try:
        amount = float(rest[1])
    except ValueError:
        await msg.answer("Amount must be a number.")
        return
    currency = db.normalize_currency(rest[2], cfg.default_currency)
    frequency = rest[3].lower()
    next_due = rest[4]
    type_ = rest[5].lower() if len(rest) > 5 else "expense"

    if frequency not in RECURRING_FREQUENCIES:
        await msg.answer("Frequency must be daily/weekly/monthly/yearly.")
        return
    try:
        date.fromisoformat(next_due)
    except ValueError:
        await msg.answer("next_due must be YYYY-MM-DD.")
        return
    if type_ not in ("expense", "income"):
        type_ = "expense"
    minor = db.valid_minor(amount, currency)
    if minor is None:
        await msg.answer("Amount must be a positive number.")
        return

    await recurring.add_item(
        description=description,
        amount_minor=minor,
        currency=currency,
        type=type_,
        frequency=frequency,
        next_due=next_due,
    )
    await msg.answer("Recurring item added.")


async def _recurring_loop(bot: Bot, cfg: Config) -> None:
    while True:
        await asyncio.sleep(3600)
        await recurring.check_due(bot, cfg)


async def main(cfg: Config) -> None:
    bot = Bot(token=cfg.telegram_token)
    await db.init_db()
    task = None
    try:
        await startup(bot, cfg)
        await recurring.check_due(bot, cfg)
        if cfg.group_id is not None:
            await capture.resume_pending(bot, cfg.group_id)
        dp = build_dispatcher(bot, cfg)
        task = asyncio.create_task(_recurring_loop(bot, cfg))
        await dp.start_polling(bot)
    finally:
        if task is not None:
            task.cancel()
        await db.close_db()
