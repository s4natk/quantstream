from quantstream.redis_io import publish_tick
from quantstream.stream import tick_from_fields
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
