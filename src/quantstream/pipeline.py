from dataclasses import dataclass, field
from datetime import datetime

from quantstream.candles import CandleBuilder
from quantstream.config import Settings
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

    @classmethod
    def from_settings(cls, settings: Settings) -> "Pipeline":
        return cls(
            settings.candle_interval_seconds,
            settings.volatility_window,
            settings.volatility_threshold,
        )

    def on_tick(self, tick: Tick, now: datetime) -> Outcome:
        symbol = tick.symbol.strip().upper()
        if symbol != tick.symbol:
            tick = Tick(symbol, tick.price, tick.size, tick.ts)
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

    def on_batch(self, messages: list[tuple[str, dict[str, str]]], now: datetime) -> Outcome:
        closed: list[Candle] = []
        alerts: list[Alert] = []
        failed: list[tuple[str, str]] = []
        for message_id, fields in messages:
            outcome = self.on_fields(message_id, fields, now)
            closed.extend(outcome.closed)
            alerts.extend(outcome.alerts)
            failed.extend(outcome.failed)
        return Outcome(closed, alerts, failed)
