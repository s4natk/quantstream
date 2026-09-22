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
