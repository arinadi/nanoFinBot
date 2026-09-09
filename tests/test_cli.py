"""Tests for the nfb CLI (setup and version)."""

import builtins

import pytest

from nanofinbot import cli
from nanofinbot.config import Config


def test_setup_writes_token_and_no_group(monkeypatch):
    saved = {}
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": "tok123")
    monkeypatch.setattr(builtins, "input", lambda prompt="": "")
    monkeypatch.setattr(cli, "load_config", lambda: Config())
    monkeypatch.setattr(cli, "save_config", lambda cfg: saved.update(cfg=cfg))

    assert cli.cmd_setup() == 0
    assert saved["cfg"].telegram_token == "tok123"
    assert saved["cfg"].group_id is None


def test_setup_parses_group_id(monkeypatch):
    saved = {}
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": "tok")
    monkeypatch.setattr(builtins, "input", lambda prompt="": "123456")
    monkeypatch.setattr(cli, "load_config", lambda: Config())
    monkeypatch.setattr(cli, "save_config", lambda cfg: saved.update(cfg=cfg))

    assert cli.cmd_setup() == 0
    assert saved["cfg"].group_id == 123456


def test_setup_negative_group_id(monkeypatch):
    saved = {}
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": "tok")
    monkeypatch.setattr(builtins, "input", lambda prompt="": "-1001234567890")
    monkeypatch.setattr(cli, "load_config", lambda: Config())
    monkeypatch.setattr(cli, "save_config", lambda cfg: saved.update(cfg=cfg))

    assert cli.cmd_setup() == 0
    assert saved["cfg"].group_id == -1001234567890


def test_setup_invalid_group_id_becomes_none(monkeypatch):
    saved = {}
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": "tok")
    monkeypatch.setattr(builtins, "input", lambda prompt="": "not-a-number")
    monkeypatch.setattr(cli, "load_config", lambda: Config())
    monkeypatch.setattr(cli, "save_config", lambda cfg: saved.update(cfg=cfg))

    assert cli.cmd_setup() == 0
    assert saved["cfg"].group_id is None


def test_version_exits_zero():
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--version"])
    assert excinfo.value.code == 0
