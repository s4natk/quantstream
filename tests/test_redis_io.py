import pytest
from tests.fakes import FakeRedis
from tests.support import make_tick

from quantstream.redis_io import (
    acknowledge,
    ensure_group,
    parse_entries,
    parse_group_reply,
    publish_tick,
    read_group,
)
from quantstream.stream import tick_from_fields, tick_to_fields


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


def test_empty_reply_has_no_ticks():
    assert parse_group_reply(None) == []
    assert parse_group_reply([]) == []


async def test_read_group_requests_new_messages():
    client = FakeRedis()
    tick = make_tick()
    client.reply = [("ticks", [("9-0", tick_to_fields(tick))])]
    found = await read_group(client, "ticks", "candles", "worker-1", 200, 2000)
    assert found == [("9-0", tick)]
    kind, group, consumer, streams, count, block = client.calls[0]
    assert kind == "xreadgroup"
    assert group == "candles"
    assert consumer == "worker-1"
    assert streams == {"ticks": ">"}
    assert count == 200
    assert block == 2000


async def test_acknowledge_forwards_ids_and_skips_empty():
    client = FakeRedis()
    assert await acknowledge(client, "ticks", "candles", []) == 0
    assert client.calls == []
    assert await acknowledge(client, "ticks", "candles", ["1-0", "2-0"]) == 2
    assert client.calls[-1] == ("xack", "ticks", "candles", ("1-0", "2-0"))
