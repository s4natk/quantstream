from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from quantstream.db import AlertRow, CandleRow
from quantstream.models import Candle
from quantstream.records import candle_values


def upsert_candle_stmt(candle: Candle):
    values = candle_values(candle)
    statement = insert(CandleRow).values(**values)
    return statement.on_conflict_do_update(
        constraint="uq_candles_symbol_bucket",
        set_={
            "open": statement.excluded.open,
            "high": statement.excluded.high,
            "low": statement.excluded.low,
            "close": statement.excluded.close,
            "volume": statement.excluded.volume,
            "trade_count": statement.excluded.trade_count,
        },
    )


def recent_candles_stmt(symbol: str, limit: int):
    return (
        select(CandleRow)
        .where(CandleRow.symbol == symbol)
        .order_by(CandleRow.bucket.desc())
        .limit(limit)
    )


def recent_alerts_stmt(symbol: str, limit: int):
    return (
        select(AlertRow)
        .where(AlertRow.symbol == symbol)
        .order_by(AlertRow.bucket.desc())
        .limit(limit)
    )
