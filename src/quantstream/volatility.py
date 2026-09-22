import math
from collections import deque

from quantstream.models import Alert, Candle


def realized_vol(closes: list[float]) -> float | None:
    if len(closes) < 3:
        return None
    returns: list[float] = []
    for prev, curr in zip(closes, closes[1:]):
        if prev <= 0 or curr <= 0:
            return None
        returns.append(math.log(curr / prev))
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
    return math.sqrt(variance)


class VolatilityTracker:
    def __init__(self, window: int, threshold: float) -> None:
        if window < 3:
            raise ValueError("window must cover at least three closes")
        self.window = window
        self.threshold = threshold
        self._closes: dict[str, deque[float]] = {}

    def observe(self, candle: Candle) -> Alert | None:
        series = self._closes.setdefault(candle.symbol, deque(maxlen=self.window))
        series.append(candle.close)
        vol = realized_vol(list(series))
        if vol is None or vol < self.threshold:
            return None
        return Alert(
            symbol=candle.symbol,
            bucket=candle.bucket,
            volatility=vol,
            threshold=self.threshold,
        )

    def closes(self, symbol: str) -> list[float]:
        series = self._closes.get(symbol)
        if series is None:
            return []
        return list(series)

    def reading(self, symbol: str) -> float | None:
        series = self._closes.get(symbol)
        if series is None:
            return None
        return realized_vol(list(series))
