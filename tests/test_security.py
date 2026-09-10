"""Tests for authorization."""

from nanofinbot.config import Config
from nanofinbot.security import authorized


def test_authorized_group_chat():
    cfg = Config(telegram_token="x", group_id=123)
    assert authorized(cfg, 123) is True
    assert authorized(cfg, 456) is False
    assert authorized(cfg, None) is False


def test_authorized_no_group_denies_all():
    cfg = Config(telegram_token="x", group_id=None)
    assert authorized(cfg, 123) is False
