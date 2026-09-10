"""Provider settings helpers for the /settings UI."""

from __future__ import annotations

from nanofinbot.config import Config, ProviderSettings


def mask_key(key: str) -> str:
    if not key:
        return "(none)"
    if len(key) <= 4:
        return "****"
    return f"{key[:4]}…"


def format_provider(p: ProviderSettings) -> str:
    base = p.base_url or "(not set)"
    model = p.model or "(not set)"
    return f"{base} / {model} / {mask_key(p.api_key)}"


def settings_text(cfg: Config) -> str:
    lines = [
        "Settings:",
        f"Text provider: {format_provider(cfg.provider)}",
    ]
    if cfg.image_provider:
        lines.append(f"Image provider: {format_provider(cfg.image_provider)}")
    else:
        lines.append("Image provider: (falls back to text provider)")
    return "\n".join(lines)


def set_text_provider(cfg: Config, base_url: str, model: str, api_key: str) -> None:
    cfg.provider = ProviderSettings(base_url=base_url, model=model, api_key=api_key)


def set_image_provider(cfg: Config, base_url: str, model: str, api_key: str) -> None:
    cfg.image_provider = ProviderSettings(base_url=base_url, model=model, api_key=api_key)


def clear_image_provider(cfg: Config) -> None:
    cfg.image_provider = None


def provider_status_text(cfg: Config) -> str:
    p = cfg.provider
    if p.base_url and p.model and p.api_key:
        image = cfg.image_provider
        if image and image.base_url and image.model and image.api_key:
            return f"Provider ready: {p.model} · image: {image.model}"
        return f"Provider ready: {p.model} · image: text provider"
    missing = [
        name for name, value in (
            ("base_url", p.base_url), ("model", p.model), ("api_key", p.api_key),
        ) if not value
    ]
    return (
        f"Provider not configured ({', '.join(missing)} missing). "
        "Text entry works (rules-only); photo OCR and auto-categorize are disabled. "
        "Run /settings to configure."
    )
