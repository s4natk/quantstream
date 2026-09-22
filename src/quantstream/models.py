from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Tick:
    symbol: str
    price: float
    size: float
    ts: datetime


@dataclass(frozen=True, slots=True)
class Candle:
    symbol: str
    bucket: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    trade_count: int


@dataclass(frozen=True, slots=True)
class Alert:
    symbol: str
    bucket: datetime
    volatility: float
    threshold: float
