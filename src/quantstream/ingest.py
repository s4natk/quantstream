import asyncio

import websockets

from quantstream.config import get_settings
from quantstream.feed import TradeParseError, parse_trade
from quantstream.redis_io import make_redis, publish_tick


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


async def run() -> None:
    settings = get_settings()
    allowed = set(settings.symbol_list()) or None
    client = make_redis(settings.redis_url)
    try:
        async with websockets.connect(settings.feed_url) as websocket:
            await consume_socket(websocket, client, settings.stream_key, allowed)
    finally:
        await client.aclose()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
