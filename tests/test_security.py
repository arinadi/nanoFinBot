"""Tests for authorization."""

from nanofinbot.config import Config
from nanofinbot.security import authorized, is_bootstrap


def test_authorized_group_chat():
    cfg = Config(telegram_token="x", group_id=123)
    assert authorized(cfg, 123) is True
    assert authorized(cfg, 456) is False
    assert authorized(cfg, None) is False


def test_authorized_no_group_denies_all():
    cfg = Config(telegram_token="x", group_id=None)
    assert authorized(cfg, 123) is False


def test_is_bootstrap():
    assert is_bootstrap("/chatid") is True
    assert is_bootstrap("/id") is True
    assert is_bootstrap("/id@somebot") is True
    assert is_bootstrap("spend 50 pizza") is False
    assert is_bootstrap(None) is False
