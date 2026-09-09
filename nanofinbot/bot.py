"""aiogram bot: startup status, long polling, and message/callback routing."""

from __future__ import annotations

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from nanofinbot import __version__, capture, db, recurring, reports, settings
from nanofinbot.config import Config, save_config
from nanofinbot.provider import Provider

_settings_state: dict[int, str] = {}


async def startup(bot: Bot, cfg: Config) -> None:
    """Send exactly one status message to the configured group on start."""
    if cfg.group_id is None:
        return
    await bot.send_message(cfg.group_id, f"nanoFinBot {__version__} online")


def build_dispatcher(bot: Bot, cfg: Config) -> Dispatcher:
    dp = Dispatcher()
    provider = Provider.from_config(cfg)

    @dp.message(CommandStart())
    async def cmd_start(msg: Message) -> None:
        await msg.answer("Hi! Send a photo or text like `spend 50 pizza`.")

    @dp.message(Command("list"))
    async def cmd_list(msg: Message) -> None:
        await capture.on_list(bot, msg.chat.id)

    @dp.message(Command("report"))
    async def cmd_report(msg: Message) -> None:
        rows = await db.list_transactions(status="active")
        pdf = reports.build_pdf(rows)
        await msg.answer_document(BufferedInputFile(pdf, filename="report.pdf"))

    @dp.message(Command("export"))
    async def cmd_export(msg: Message) -> None:
        rows = await db.list_transactions(status="active")
        csv_bytes = reports.build_csv(rows)
        await msg.answer_document(BufferedInputFile(csv_bytes, filename="export.csv"))

    @dp.message(Command("categories"))
    async def cmd_categories(msg: Message) -> None:
        cats = await db.list_categories()
        if not cats:
            await msg.answer("No categories yet.")
            return
        await msg.answer("\n".join(f"- {c['id']}: {c['name']}" for c in cats))

    @dp.message(Command("rename"))
    async def cmd_rename(msg: Message) -> None:
        parts = msg.text.split(maxsplit=2)
        if len(parts) < 3:
            await msg.answer("Usage: /rename <id> <new name>")
            return
        try:
            category_id = int(parts[1])
        except ValueError:
            await msg.answer("Category id must be a number.")
            return
        ok = await db.rename_category(category_id, parts[2])
        await msg.answer("Renamed." if ok else "Rename failed (duplicate or empty name).")

    @dp.message(Command("recurring"))
    async def cmd_recurring(msg: Message) -> None:
        args = msg.text.split()[1:]
        if args and args[0] == "add" and len(args) >= 6:
            description = args[1]
            amount = float(args[2])
            currency = args[3].upper()
            frequency = args[4]
            next_due = args[5]
            await recurring.add_item(
                description=description,
                amount_minor=db.to_minor(amount, currency),
                currency=currency,
                frequency=frequency,
                next_due=next_due,
            )
            await msg.answer("Recurring item added.")
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
        photo = msg.photo[-1]
        data = await bot.download(photo)
        image_bytes = data.read() if data is not None else b""
        await capture.on_photo(bot, cfg, provider, msg.chat.id, msg.from_user.id, image_bytes)

    @dp.message(F.text)
    async def on_text_msg(msg: Message) -> None:
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


async def main(cfg: Config) -> None:
    bot = Bot(token=cfg.telegram_token)
    await db.init_db()
    try:
        await startup(bot, cfg)
        await recurring.check_due(bot, cfg)
        dp = build_dispatcher(bot, cfg)
        await dp.start_polling(bot)
    finally:
        await db.close_db()
