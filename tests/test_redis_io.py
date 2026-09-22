import pytest

from quantstream.redis_io import ensure_group, parse_entries, publish_tick
from quantstream.stream import tick_from_fields, tick_to_fields
from tests.fakes import FakeRedis
from tests.support import make_tick


async def test_publish_writes_tick_fields():
    client = FakeRedis()
    tick = make_tick(price=42.5, size=3)
    message_id = await publish_tick(client, "ticks", tick)
    assert message_id == "1710000000000-0"
    kind, key, fields = client.calls[0]
    assert kind == "xadd"
    assert key == "ticks"
    assert tick_from_fields(fields) == tick


async def test_existing_group_is_left_alone():
    client = FakeRedis()
    client.error = RuntimeError("BUSYGROUP Consumer Group name already exists")
    await ensure_group(client, "ticks", "candles")
    assert client.calls[0][0] == "xgroup"


async def test_unexpected_group_error_is_raised():
    client = FakeRedis()
    client.error = RuntimeError("NOAUTH")
    with pytest.raises(RuntimeError):
        await ensure_group(client, "ticks", "candles")


def test_parse_entries_keeps_ids():
    tick = make_tick(symbol="MSFT", price=10.0)
    parsed = parse_entries([("4-1", tick_to_fields(tick))])
    assert parsed == [("4-1", tick)]
