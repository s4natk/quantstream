from datetime import timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from quantstream.models import Candle

SCHEMA = pa.schema(
    [
        ("symbol", pa.string()),
        ("bucket", pa.timestamp("us")),
        ("open", pa.float64()),
        ("high", pa.float64()),
        ("low", pa.float64()),
        ("close", pa.float64()),
        ("volume", pa.float64()),
        ("trade_count", pa.int64()),
    ]
)


def _as_utc_naive(bucket):
    if bucket.tzinfo is None:
        return bucket
    return bucket.astimezone(timezone.utc).replace(tzinfo=None)


def candles_to_table(candles: list[Candle]) -> pa.Table:
    rows = [
        {
            "symbol": candle.symbol,
            "bucket": _as_utc_naive(candle.bucket),
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
            "trade_count": candle.trade_count,
        }
        for candle in candles
    ]
    return pa.Table.from_pylist(rows, schema=SCHEMA)


def write_candles(path: Path, candles: list[Candle]) -> None:
    pq.write_table(candles_to_table(candles), path)


def read_candles(path: Path) -> list[Candle]:
    table = pq.read_table(path, schema=SCHEMA)
    return [
        Candle(
            symbol=row["symbol"],
            bucket=row["bucket"].replace(tzinfo=timezone.utc),
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
            trade_count=row["trade_count"],
        )
        for row in table.to_pylist()
    ]
