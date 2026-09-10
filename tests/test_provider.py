"""Tests for the provider client against local mock OpenAI endpoints."""

from contextlib import asynccontextmanager

import pytest
from aiohttp import web

from nanofinbot.config import ProviderSettings
from nanofinbot.provider import Provider, ProviderAuthError, ProviderError, ProviderNotConfigured


@asynccontextmanager
async def serve(app: web.Application):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        yield port
    finally:
        await runner.cleanup()


def content_app(content: str) -> web.Application:
    async def handler(request):
        return web.json_response({"choices": [{"message": {"role": "assistant", "content": content}}]})

    app = web.Application()
    app.router.add_post("/v1/chat/completions", handler)
    return app


async def test_text():
    async with serve(content_app("hello world")) as port:
        provider = Provider(ProviderSettings(base_url=f"http://127.0.0.1:{port}/v1", model="m", api_key="k"))
        out = await provider.text("sys", "hi")
        assert out == "hello world"


async def test_image_provider_override():
    async with serve(content_app("TEXT-RESULT")) as text_port:
        async with serve(content_app("IMAGE-RESULT")) as image_port:
            text_settings = ProviderSettings(base_url=f"http://127.0.0.1:{text_port}/v1", model="t", api_key="k")
            image_settings = ProviderSettings(base_url=f"http://127.0.0.1:{image_port}/v1", model="i", api_key="k")

            provider = Provider(text_settings, image_provider=image_settings)
            assert await provider.vision("sys", b"fake-image") == "IMAGE-RESULT"

            fallback = Provider(text_settings, image_provider=None)
            assert await fallback.vision("sys", b"fake-image") == "TEXT-RESULT"


async def test_auth_error():
    async def handler(request):
        return web.Response(status=401, text="Unauthorized")

    app = web.Application()
    app.router.add_post("/v1/chat/completions", handler)

    async with serve(app) as port:
        provider = Provider(ProviderSettings(base_url=f"http://127.0.0.1:{port}/v1", model="m", api_key="bad"))
        with pytest.raises(ProviderAuthError):
            await provider.text("sys", "hi")


async def test_not_configured():
    provider = Provider(ProviderSettings(base_url="", model="", api_key=""))
    with pytest.raises(ProviderNotConfigured):
        await provider.text("sys", "hi")


async def test_generic_error():
    async def handler(request):
        return web.Response(status=500, text="boom")

    app = web.Application()
    app.router.add_post("/v1/chat/completions", handler)

    async with serve(app) as port:
        provider = Provider(ProviderSettings(base_url=f"http://127.0.0.1:{port}/v1", model="m", api_key="k"))
        with pytest.raises(ProviderError):
            await provider.text("sys", "hi")


async def test_html_error_truncated():
    html = "<!DOCTYPE html><title>Not Found</title>" + "x" * 5000

    async def handler(request):
        return web.Response(status=404, text=html, content_type="text/html")

    app = web.Application()
    app.router.add_post("/v1/chat/completions", handler)

    async with serve(app) as port:
        provider = Provider(ProviderSettings(base_url=f"http://127.0.0.1:{port}/v1", model="m", api_key="k"))
        with pytest.raises(ProviderError) as excinfo:
            await provider.text("sys", "hi")
    assert "404" in str(excinfo.value)
    assert len(str(excinfo.value)) < 500
