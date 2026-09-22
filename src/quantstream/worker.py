from datetime import datetime

from quantstream.config import Settings
from quantstream.pipeline import Outcome, Pipeline
from quantstream.redis_io import acknowledge, read_raw
from quantstream.storage import write_alert, write_candle


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
