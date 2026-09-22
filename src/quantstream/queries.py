from sqlalchemy.dialects.postgresql import insert

from quantstream.db import CandleRow
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
