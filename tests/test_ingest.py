import json

from quantstream.feed import parse_trade
from quantstream.ingest import handle_message
from tests.fakes import FakeRedis


def _payload(symbol: str, price: float = 10.0) -> str:
    return json.dumps(
        {"symbol": symbol, "price": price, "size": 1, "ts": "2026-09-22T14:00:01+00:00"}
    )


async def test_handle_message_publishes_an_allowed_trade():
    client = FakeRedis()
    message_id = await handle_message(client, "ticks", _payload("aapl"), {"AAPL"})
    assert message_id == "1710000000000-0"
    assert parse_trade(_payload("AAPL")).symbol == "AAPL"
    assert client.calls[0][0] == "xadd"


async def test_handle_message_skips_bad_or_unlisted_trades():
    client = FakeRedis()
    assert await handle_message(client, "ticks", "nope", {"AAPL"}) is None
    assert await handle_message(client, "ticks", _payload("MSFT"), {"AAPL"}) is None
    assert client.calls == []
