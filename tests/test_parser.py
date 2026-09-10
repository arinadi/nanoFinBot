"""Tests for the rules-based parser and LLM categorization."""

from nanofinbot.parser import Draft, categorize, parse


def test_spend():
    d = parse("spend 50 pizza", "USD")
    assert d.type == "expense"
    assert d.amount_minor == 5000
    assert d.currency == "USD"
    assert d.description == "pizza"


def test_income():
    d = parse("+3500 salary", "IDR")
    assert d.type == "income"
    assert d.amount_minor == 3500
    assert d.description == "salary"


def test_plain_amount():
    d = parse("50 coffee", "USD")
    assert d.type == "expense"
    assert d.amount_minor == 5000
    assert d.description == "coffee"


def test_unparseable():
    d = parse("hello", "USD")
    assert d.amount_minor is None
    assert d.reason


def test_zero_amount_rejected():
    d = parse("spend 0 pizza", "USD")
    assert d.amount_minor is None


def test_currency_code_override():
    d = parse("spend 50 USD pizza", "IDR")
    assert d.currency == "USD"
    assert d.amount_minor == 5000


def test_currency_symbol():
    d = parse("Rp 12500", "USD")
    assert d.currency == "IDR"
    assert d.amount_minor == 12500


class FakeProvider:
    def __init__(self, content, configured=True):
        self.content = content
        self.configured = configured

    async def text(self, system, user, json_mode=False):
        return self.content


async def test_categorize_llm():
    d = Draft(description="pizza")
    provider = FakeProvider('{"category": "Food"}')
    assert await categorize(d, provider) == "Food"


async def test_categorize_no_provider():
    d = Draft(description="pizza")
    assert await categorize(d, None) is None


async def test_categorize_bad_json():
    d = Draft(description="pizza")
    provider = FakeProvider("not json at all")
    assert await categorize(d, provider) is None
