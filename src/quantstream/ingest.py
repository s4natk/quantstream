from quantstream.feed import TradeParseError, parse_trade
from quantstream.redis_io import publish_tick


async def handle_message(client, stream_key: str, payload: str, allowed: set[str] | None = None):
    try:
        tick = parse_trade(payload)
    except TradeParseError:
        return None
    if allowed is not None and tick.symbol not in allowed:
        return None
    return await publish_tick(client, stream_key, tick)


async def consume_socket(
    websocket,
    client,
    stream_key: str,
    allowed: set[str] | None = None,
) -> int:
    published = 0
    async for payload in websocket:
        message_id = await handle_message(client, stream_key, payload, allowed)
        if message_id is not None:
            published += 1
    return published
