from redis.asyncio import Redis

from quantstream.models import Tick
from quantstream.stream import tick_from_fields, tick_to_fields


def make_redis(url: str) -> Redis:
    return Redis.from_url(url, decode_responses=True)


async def publish_tick(client, stream_key: str, tick: Tick) -> str:
    message_id = await client.xadd(stream_key, tick_to_fields(tick))
    return str(message_id)


async def ensure_group(client, stream_key: str, group: str) -> None:
    try:
        await client.xgroup_create(stream_key, group, id="0", mkstream=True)
    except Exception as exc:
        if "BUSYGROUP" in str(exc):
            return
        raise


def parse_entries(messages: list[tuple[str, dict[str, str]]]) -> list[tuple[str, Tick]]:
    return [(str(message_id), tick_from_fields(fields)) for message_id, fields in messages]


def parse_group_reply(reply) -> list[tuple[str, Tick]]:
    if not reply:
        return []
    parsed: list[tuple[str, Tick]] = []
    for _stream, messages in reply:
        parsed.extend(parse_entries(messages))
    return parsed


async def read_group(client, stream_key: str, group: str, consumer: str, count: int, block_ms: int):
    reply = await client.xreadgroup(
        groupname=group,
        consumername=consumer,
        streams={stream_key: ">"},
        count=count,
        block=block_ms,
    )
    return parse_group_reply(reply)
