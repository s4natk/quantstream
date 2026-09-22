from datetime import datetime, timedelta, timezone

from quantstream.models import Candle, Tick


def make_tick(
    symbol: str = "AAPL",
    price: float = 100.0,
    size: float = 1.0,
    minute: int = 0,
    second: int = 1,
) -> Tick:
    ts = datetime(2026, 9, 21, 14, 0, second, tzinfo=timezone.utc)
    return Tick(symbol, price, size, ts + timedelta(minutes=minute))


def make_candle(symbol: str = "AAPL", close: float = 100.0, minute: int = 0) -> Candle:
    bucket = datetime(2026, 9, 21, 14, 0, tzinfo=timezone.utc) + timedelta(minutes=minute)
    return Candle(symbol, bucket, close, close, close, close, 1.0, 1)
