from dataclasses import dataclass, field
from datetime import datetime

from quantstream.candles import CandleBuilder
from quantstream.models import Alert, Candle, Tick
from quantstream.stream import TickDecodeError, tick_from_fields
from quantstream.volatility import VolatilityTracker


@dataclass(frozen=True, slots=True)
class Outcome:
    closed: list[Candle]
    alerts: list[Alert]
    failed: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class Counters:
    ticks: int = 0
    candles: int = 0
    alerts: int = 0
    failed: int = 0


class Pipeline:
    def __init__(self, interval_seconds: int, window: int, threshold: float) -> None:
        self.builder = CandleBuilder(interval_seconds)
        self.tracker = VolatilityTracker(window, threshold)
        self.counters = Counters()

    def on_tick(self, tick: Tick, now: datetime) -> Outcome:
        self.builder.add(tick)
        self.counters.ticks += 1
        return self._close(now)

    def _close(self, now: datetime) -> Outcome:
        closed = self.builder.drain(now)
        alerts: list[Alert] = []
        for candle in closed:
            found = self.tracker.observe(candle)
            if found is not None:
                alerts.append(found)
        self.counters.candles += len(closed)
        self.counters.alerts += len(alerts)
        return Outcome(closed, alerts)

    def on_fields(self, message_id: str, fields: dict[str, str], now: datetime) -> Outcome:
        try:
            tick = tick_from_fields(fields)
        except TickDecodeError as exc:
            self.counters.failed += 1
            return Outcome(closed=[], alerts=[], failed=[(message_id, str(exc))])
        return self.on_tick(tick, now)
