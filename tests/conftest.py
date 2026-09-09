"""Shared pytest fixtures for nanoFinBot."""

from __future__ import annotations

import pytest

from nanofinbot import db


@pytest.fixture
def tmp_config_dir(tmp_path):
    """A temporary directory that acts as the user config dir."""
    d = tmp_path / "config"
    d.mkdir()
    return d


@pytest.fixture
def tmp_db_path(tmp_path):
    """A temporary SQLite database path."""
    return tmp_path / "data" / "nfb.db"


@pytest.fixture
async def fresh_db(tmp_db_path):
    """Initialize a fresh database for the duration of a test."""
    await db.init_db(tmp_db_path)
    yield
    await db.close_db()


class FakeBot:
    """A bot double that records messages and documents."""

    def __init__(self):
        self.sent = []
        self.documents = []
        self.answered = []

    async def send_message(self, chat_id, text, reply_markup=None):
        self.sent.append(
            {"chat_id": chat_id, "text": text, "reply_markup": reply_markup}
        )
        return len(self.sent)

    async def answer_document(self, chat_id, document, caption=None):
        self.documents.append(
            {"chat_id": chat_id, "document": document, "caption": caption}
        )

    async def answer_callback_query(self, callback_query_id, text=None):
        self.answered.append({"query_id": callback_query_id, "text": text})


@pytest.fixture
def fake_bot():
    return FakeBot()
