import asyncio
from datetime import datetime, timezone

from quantstream.config import Settings, get_settings
from quantstream.pipeline import Outcome, Pipeline
from quantstream.redis_io import acknowledge, ensure_group, make_redis, read_raw
from quantstream.session import create_tables, make_engine, make_session_factory
from quantstream.storage import write_alert, write_candle


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def persist_outcome(session, outcome: Outcome) -> None:
    for candle in outcome.closed:
        await write_candle(session, candle)
    for alert in outcome.alerts:
        await write_alert(session, alert)
    await session.commit()


async def process_once(
    client,
    sessions,
    pipeline: Pipeline,
    settings: Settings,
    now: datetime,
) -> Outcome:
    messages = await read_raw(
        client,
        settings.stream_key,
        settings.consumer_group,
        settings.consumer_name,
        settings.stream_read_count,
        settings.stream_block_ms,
    )
    outcome = pipeline.on_batch(messages, now)
    if outcome.closed or outcome.alerts:
        async with sessions() as session:
            await persist_outcome(session, outcome)
    message_ids = [message_id for message_id, _fields in messages]
    await acknowledge(client, settings.stream_key, settings.consumer_group, message_ids)
    return outcome


async def run_batches(client, sessions, pipeline, settings: Settings, now: datetime, batches: int):
    await ensure_group(client, settings.stream_key, settings.consumer_group)
    results = []
    for _ in range(batches):
        results.append(await process_once(client, sessions, pipeline, settings, now))
    return results


async def serve() -> None:
    settings = get_settings()
    client = make_redis(settings.redis_url)
    engine = make_engine(settings.database_url)
    sessions = make_session_factory(engine)
    pipeline = Pipeline.from_settings(settings)
    await create_tables(engine)
    try:
        await ensure_group(client, settings.stream_key, settings.consumer_group)
        while True:
            await process_once(client, sessions, pipeline, settings, utcnow())
    finally:
        await client.aclose()
        await engine.dispose()


def main() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    main()
