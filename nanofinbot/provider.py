"""OpenAI-compatible provider client.

One SDK drives every provider via a configurable ``base_url`` (see
reference/openai-sdk.md). Text and vision calls run in a worker thread so the bot
event loop is never blocked.
"""

from __future__ import annotations

import asyncio
import base64

from openai import APIConnectionError, APIError, AuthenticationError, OpenAI

from nanofinbot.config import Config, ProviderSettings


class ProviderError(Exception):
    """Base error for provider calls."""


class ProviderAuthError(ProviderError):
    """The provider rejected the API key (401)."""


class ProviderNetworkError(ProviderError):
    """The provider endpoint was unreachable."""


class ProviderNotConfigured(ProviderError):
    """No provider is configured."""


def _format_api_error(exc: APIError) -> str:
    status = getattr(exc, "status_code", None)
    snippet = ""
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        err = body.get("error", {})
        snippet = err.get("message", "") if isinstance(err, dict) else str(err)
    if not snippet:
        snippet = str(body if body else getattr(exc, "message", ""))
    snippet = " ".join(snippet.split())[:300]
    if status is not None:
        return f"provider error (HTTP {status}): {snippet}"
    return f"provider error: {snippet}"


class _Client:
    def __init__(self, settings: ProviderSettings):
        self.base_url = settings.base_url
        self.model = settings.model
        self.api_key = settings.api_key
        self._openai = (
            OpenAI(base_url=settings.base_url, api_key=settings.api_key)
            if settings.configured
            else None
        )

    @property
    def configured(self) -> bool:
        return self._openai is not None

    def _complete(self, messages: list[dict], json_mode: bool):
        kwargs: dict = {"model": self.model, "messages": messages}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        return self._openai.chat.completions.create(**kwargs)

    async def _run(self, messages: list[dict], json_mode: bool) -> str:
        if not self.configured:
            raise ProviderNotConfigured("no provider configured")
        try:
            resp = await asyncio.to_thread(self._complete, messages, json_mode)
        except AuthenticationError as exc:
            raise ProviderAuthError("provider rejected the API key (401)") from exc
        except APIConnectionError as exc:
            raise ProviderNetworkError("provider unreachable") from exc
        except APIError as exc:
            raise ProviderError(_format_api_error(exc)) from exc
        content = resp.choices[0].message.content
        return content or ""

    async def text(self, system: str, user: str, json_mode: bool = False) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return await self._run(messages, json_mode)

    async def vision(self, system: str, image_bytes: bytes, json_mode: bool = False) -> str:
        data_uri = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": system},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            }
        ]
        return await self._run(messages, json_mode)


class Provider:
    """Aggregates a text client and an optional image client."""

    def __init__(self, provider: ProviderSettings, image_provider: ProviderSettings | None = None):
        self._text = _Client(provider)
        self._image = _Client(image_provider) if (image_provider and image_provider.configured) else self._text

    @property
    def configured(self) -> bool:
        return self._text.configured

    async def text(self, system: str, user: str, json_mode: bool = False) -> str:
        return await self._text.text(system, user, json_mode)

    async def vision(self, system: str, image_bytes: bytes, json_mode: bool = False) -> str:
        return await self._image.vision(system, image_bytes, json_mode)

    @classmethod
    def from_config(cls, cfg: Config) -> "Provider":
        return cls(cfg.provider, cfg.image_provider)
