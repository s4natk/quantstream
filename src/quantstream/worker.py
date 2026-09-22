from quantstream.pipeline import Outcome
from quantstream.storage import write_alert, write_candle


async def persist_outcome(session, outcome: Outcome) -> None:
    for candle in outcome.closed:
        await write_candle(session, candle)
    for alert in outcome.alerts:
        await write_alert(session, alert)
    await session.commit()
