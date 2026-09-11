"""Placeholder test that proves the async test scaffold works."""



async def test_placeholder_async():
    result = await _echo(42)
    assert result == 42


async def _echo(value: int) -> int:
    return value
