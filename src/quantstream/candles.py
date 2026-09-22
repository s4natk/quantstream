from datetime import datetime, timezone

from quantstream.models import Candle, Tick


def bucket_start(ts: datetime, interval_seconds: int) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    epoch = int(ts.timestamp())
    aligned = epoch - (epoch % interval_seconds)
    return datetime.fromtimestamp(aligned, tz=timezone.utc)


class CandleBuilder:
    def __init__(self, interval_seconds: int) -> None:
        self.interval_seconds = interval_seconds
        self._open: dict[tuple[str, datetime], Candle] = {}

    def add(self, tick: Tick) -> Candle:
        bucket = bucket_start(tick.ts, self.interval_seconds)
        key = (tick.symbol, bucket)
        current = self._open.get(key)
        if current is None:
            candle = Candle(
                symbol=tick.symbol,
                bucket=bucket,
                open=tick.price,
                high=tick.price,
                low=tick.price,
                close=tick.price,
                volume=tick.size,
                trade_count=1,
            )
        else:
            candle = Candle(
                symbol=current.symbol,
                bucket=current.bucket,
                open=current.open,
                high=max(current.high, tick.price),
                low=min(current.low, tick.price),
                close=tick.price,
                volume=current.volume + tick.size,
                trade_count=current.trade_count + 1,
            )
        self._open[key] = candle
        return candle

    def drain(self, now: datetime) -> list[Candle]:
        current = bucket_start(now, self.interval_seconds)
        ready: list[Candle] = []
        for key, candle in list(self._open.items()):
            if candle.bucket < current:
                ready.append(candle)
                del self._open[key]
        ready.sort(key=lambda item: (item.symbol, item.bucket))
        return ready

    def open_candles(self) -> list[Candle]:
        candles = list(self._open.values())
        candles.sort(key=lambda item: (item.symbol, item.bucket))
        return candles
