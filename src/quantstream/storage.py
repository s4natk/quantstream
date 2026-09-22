from quantstream.db import AlertRow
from quantstream.models import Alert, Candle
from quantstream.queries import recent_alerts_stmt, recent_candles_stmt, upsert_candle_stmt
from quantstream.records import alert_from_row, alert_values, candle_from_row


async def write_candle(session, candle: Candle) -> None:
    await session.execute(upsert_candle_stmt(candle))


async def write_alert(session, alert: Alert) -> None:
    session.add(AlertRow(**alert_values(alert)))
    await session.flush()


async def load_recent_candles(session, symbol: str, limit: int) -> list[Candle]:
    result = await session.scalars(recent_candles_stmt(symbol, limit))
    return [candle_from_row(row) for row in result.all()]


async def load_recent_alerts(session, symbol: str, limit: int) -> list[Alert]:
    result = await session.scalars(recent_alerts_stmt(symbol, limit))
    return [alert_from_row(row) for row in result.all()]
