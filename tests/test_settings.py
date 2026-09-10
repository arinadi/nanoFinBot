"""Tests for the /settings provider configuration."""

from nanofinbot import settings
from nanofinbot.config import Config, load_config, save_config
from nanofinbot.provider import Provider


def test_set_provider(tmp_config_dir):
    cfg = Config(telegram_token="x")
    settings.set_text_provider(cfg, "http://x/v1", "m", "sk-abc")
    settings.set_image_provider(cfg, "http://y/v1", "im", "sk-img")

    path = tmp_config_dir / "config.json"
    save_config(cfg, path)
    loaded = load_config(path)

    assert loaded.provider.model == "m"
    assert loaded.provider.api_key == "sk-abc"
    assert loaded.image_provider.model == "im"
    assert "sk-abc" not in settings.settings_text(loaded)  # masked


def test_mask_key():
    assert settings.mask_key("") == "(none)"
    assert settings.mask_key("abcd") == "****"
    assert settings.mask_key("sk-abc123") == "sk-a…"


async def test_clear_image_provider(tmp_config_dir):
    cfg = Config(telegram_token="x")
    settings.set_text_provider(cfg, "http://x/v1", "m", "k")
    settings.set_image_provider(cfg, "http://y/v1", "im", "k")
    path = tmp_config_dir / "config.json"
    save_config(cfg, path)

    loaded = load_config(path)
    settings.clear_image_provider(loaded)
    save_config(loaded, path)

    reloaded = load_config(path)
    assert reloaded.image_provider is None

    provider = Provider.from_config(reloaded)
    assert provider._image is provider._text
