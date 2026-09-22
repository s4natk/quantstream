from quantstream.db import AlertRow
from quantstream.models import Alert, Candle
from quantstream.queries import upsert_candle_stmt
from quantstream.records import alert_values


async def write_candle(session, candle: Candle) -> None:
    await session.execute(upsert_candle_stmt(candle))


async def write_alert(session, alert: Alert) -> None:
    session.add(AlertRow(**alert_values(alert)))
    await session.flush()
