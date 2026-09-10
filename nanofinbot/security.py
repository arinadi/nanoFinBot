"""Authorization: only the configured group chat may use the bot."""

from __future__ import annotations

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from nanofinbot.config import Config


def authorized(cfg: Config, chat_id: int | None) -> bool:
    """True only when the message comes from the configured group chat."""
    if cfg.group_id is None or chat_id is None:
        return False
    return chat_id == cfg.group_id


class AuthMiddleware(BaseMiddleware):
    """Drop any update that does not originate from the configured group chat."""

    def __init__(self, cfg: Config):
        self.cfg = cfg

    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            if not authorized(self.cfg, event.chat.id):
                return
        elif isinstance(event, CallbackQuery):
            if event.message is None or not authorized(self.cfg, event.message.chat.id):
                return
        return await handler(event, data)
