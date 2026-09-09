# aiogram 3.x — reference

Async Telegram Bot API framework. Pin major version 3.

```python
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.client.default import DefaultBotProperties
```

**Core objects**

- `Bot(token)` — API client. `await bot.send_message(chat_id, text, reply_markup=...)`,
  `await bot.send_document(chat_id, document=<BufferedInputFile or FSInputFile>)`,
  `await bot.send_photo(chat_id, photo=...)`.
- `Dispatcher()` — routes updates to handlers. `dp.start_polling(bot)` runs long polling.

**Handlers** (registered on a `Router`, then `dp.include_router(router)`)

```python
@router.message(CommandStart())            # /start
async def start(msg: Message): ...

@router.message(F.photo)                   # any message with a photo
async def on_photo(msg: Message): ...

@router.message(F.text)                    # text messages
async def on_text(msg: Message): ...

@router.callback_query(F.data == "save")   # inline button press
async def on_save(cq: CallbackQuery): ...
```

**Inline buttons**

```python
kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Save", callback_data="save")],
    [InlineKeyboardButton(text="Edit", callback_data="edit"),
     InlineKeyboardButton(text="Cancel", callback_data="cancel")],
])
await msg.answer("Draft...", reply_markup=kb)
```

- `CallbackQuery` carries `cq.data`, `cq.from_user`, `cq.message`; edit with
  `await cq.message.edit_text(...)`; answer the query with `await cq.answer(...)`.
- Photos: `msg.photo[-1]` is the largest `PhotoSize`; download via
  `await bot.download(msg.photo[-1], destination)` or `msg.photo[-1].file_id` +
  `bot.get_file(file_id)`.

**Sending a document (for PDF/CSV)** — use `aiogram.types.BufferedInputFile`:

```python
from aiogram.types import BufferedInputFile
await msg.answer_document(BufferedInputFile(pdf_bytes, filename="report.pdf"))
```

Notes the implementing agent should verify against the installed version (the API is
stable in v3 but exact import paths for `F` are `from aiogram import F`).
