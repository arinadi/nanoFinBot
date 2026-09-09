"""Tests for the startup status message."""

from nanofinbot import bot
from nanofinbot.config import Config


async def test_startup_status(fake_bot):
    cfg = Config(telegram_token="x", group_id=123)
    await bot.startup(fake_bot, cfg)
    assert len(fake_bot.sent) == 1
    assert fake_bot.sent[0]["chat_id"] == 123
    assert "nanoFinBot" in fake_bot.sent[0]["text"]


async def test_no_group(fake_bot):
    cfg = Config(telegram_token="x", group_id=None)
    await bot.startup(fake_bot, cfg)
    assert fake_bot.sent == []
