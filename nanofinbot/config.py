"""Configuration loading and saving for nanoFinBot."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

APPNAME = "nfb"

DEFAULT_CURRENCY = "IDR"
DEFAULT_TIMEZONE = "Asia/Jakarta"


class ConfigError(Exception):
    """Raised when the config file is missing required data or malformed."""


@dataclass
class ProviderSettings:
    base_url: str = ""
    model: str = ""
    api_key: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model and self.api_key)


@dataclass
class Config:
    telegram_token: str = ""
    group_id: int | None = None
    default_currency: str = DEFAULT_CURRENCY
    timezone: str = DEFAULT_TIMEZONE
    provider: ProviderSettings = field(default_factory=ProviderSettings)
    image_provider: ProviderSettings | None = None


def config_dir() -> Path:
    return Path(user_config_dir(APPNAME))


def data_dir() -> Path:
    return Path(user_data_dir(APPNAME))


def config_path() -> Path:
    return config_dir() / "config.json"


def _provider_from_dict(raw: dict | None) -> ProviderSettings:
    if not isinstance(raw, dict):
        return ProviderSettings()
    return ProviderSettings(
        base_url=str(raw.get("base_url", "") or ""),
        model=str(raw.get("model", "") or ""),
        api_key=str(raw.get("api_key", "") or ""),
    )


def _from_dict(raw: dict) -> Config:
    group_id = raw.get("group_id")
    if group_id is not None:
        try:
            group_id = int(group_id)
        except (TypeError, ValueError):
            group_id = None
    image_provider = raw.get("image_provider")
    return Config(
        telegram_token=str(raw.get("telegram_token", "") or ""),
        group_id=group_id,
        default_currency=str(raw.get("default_currency", DEFAULT_CURRENCY) or DEFAULT_CURRENCY),
        timezone=str(raw.get("timezone", DEFAULT_TIMEZONE) or DEFAULT_TIMEZONE),
        provider=_provider_from_dict(raw.get("provider")),
        image_provider=_provider_from_dict(image_provider) if image_provider else None,
    )


def _provider_to_dict(p: ProviderSettings) -> dict:
    return {"base_url": p.base_url, "model": p.model, "api_key": p.api_key}


def _to_dict(cfg: Config) -> dict:
    return {
        "telegram_token": cfg.telegram_token,
        "group_id": cfg.group_id,
        "default_currency": cfg.default_currency,
        "timezone": cfg.timezone,
        "provider": _provider_to_dict(cfg.provider),
        "image_provider": _provider_to_dict(cfg.image_provider) if cfg.image_provider else None,
    }


def load_config(path: Path | None = None) -> Config:
    p = path or config_path()
    if not p.exists():
        return Config()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ConfigError(f"config.json is malformed: {exc}. Run `nfb setup` to recreate it.") from exc
    if not isinstance(raw, dict):
        raise ConfigError("config.json must contain a JSON object. Run `nfb setup` to recreate it.")
    return _from_dict(raw)


def save_config(cfg: Config, path: Path | None = None) -> None:
    p = path or config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p.parent, 0o700)
    except OSError:
        pass
    payload = json.dumps(_to_dict(cfg), indent=2)
    fd, tmp_name = tempfile.mkstemp(dir=str(p.parent), prefix=".config-", suffix=".tmp")
    try:
        os.chmod(tmp_name, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp_name, p)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
