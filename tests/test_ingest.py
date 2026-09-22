import json

from quantstream.feed import parse_trade
from quantstream.ingest import consume_socket, handle_message
from tests.fakes import FakeRedis


class FakeSocket:
    def __init__(self, messages):
        self._messages = list(messages)
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._messages):
            raise StopAsyncIteration
        message = self._messages[self._index]
        self._index += 1
        return message


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


async def test_consume_socket_counts_published_trades():
    client = FakeRedis()
    socket = FakeSocket([_payload("AAPL"), _payload("MSFT"), "nope"])
    published = await consume_socket(socket, client, "ticks", {"AAPL", "MSFT"})
    assert published == 2
    assert len(client.calls) == 2
