from dataclasses import dataclass
from datetime import datetime

from quantstream.candles import CandleBuilder
from quantstream.models import Alert, Candle, Tick
from quantstream.volatility import VolatilityTracker


@dataclass(frozen=True, slots=True)
class Outcome:
    closed: list[Candle]
    alerts: list[Alert]


class Pipeline:
    def __init__(self, interval_seconds: int, window: int, threshold: float) -> None:
        self.builder = CandleBuilder(interval_seconds)
        self.tracker = VolatilityTracker(window, threshold)

    def on_tick(self, tick: Tick, now: datetime) -> Outcome:
        self.builder.add(tick)
        closed = self.builder.drain(now)
        alerts: list[Alert] = []
        for candle in closed:
            found = self.tracker.observe(candle)
            if found is not None:
                alerts.append(found)
        return Outcome(closed, alerts)
