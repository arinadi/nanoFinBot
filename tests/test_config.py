"""Tests for config loading/saving."""

import json

import pytest

from nanofinbot.config import (
    Config,
    ConfigError,
    ProviderSettings,
    load_config,
    save_config,
)


def test_save_load_roundtrip(tmp_config_dir):
    cfg = Config(telegram_token="tok123", group_id=None)
    cfg.provider = ProviderSettings(base_url="https://x", model="m", api_key="k")
    path = tmp_config_dir / "config.json"
    save_config(cfg, path)

    assert path.exists()
    assert not list(tmp_config_dir.glob("*.tmp"))

    loaded = load_config(path)
    assert loaded.telegram_token == "tok123"
    assert loaded.group_id is None
    assert loaded.provider.base_url == "https://x"
    assert loaded.provider.model == "m"
    assert loaded.provider.api_key == "k"


def test_defaults_when_missing(tmp_config_dir):
    cfg = load_config(tmp_config_dir / "nope.json")
    assert cfg.telegram_token == ""
    assert cfg.group_id is None
    assert cfg.default_currency == "IDR"


def test_malformed_raises_clear_error(tmp_config_dir):
    path = tmp_config_dir / "config.json"
    path.write_text("{ not json")
    with pytest.raises(ConfigError):
        load_config(path)


def test_group_id_parsed_as_int(tmp_config_dir):
    cfg = Config(telegram_token="t", group_id=None)
    path = tmp_config_dir / "config.json"
    save_config(cfg, path)
    json.loads(path.read_text())  # valid json

    raw = json.loads(path.read_text())
    raw["group_id"] = "123"
    path.write_text(json.dumps(raw))
    loaded = load_config(path)
    assert loaded.group_id == 123
