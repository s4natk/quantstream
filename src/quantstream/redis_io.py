from redis.asyncio import Redis

from quantstream.models import Tick
from quantstream.stream import tick_to_fields


def make_redis(url: str) -> Redis:
    return Redis.from_url(url, decode_responses=True)


async def publish_tick(client, stream_key: str, tick: Tick) -> str:
    message_id = await client.xadd(stream_key, tick_to_fields(tick))
    return str(message_id)
