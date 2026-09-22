from datetime import datetime

from pydantic import BaseModel

from quantstream.models import Alert, Candle


class CandleOut(BaseModel):
    symbol: str
    bucket: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    trade_count: int

    @classmethod
    def from_candle(cls, candle: Candle) -> "CandleOut":
        return cls(
            symbol=candle.symbol,
            bucket=candle.bucket,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
            trade_count=candle.trade_count,
        )


class AlertOut(BaseModel):
    symbol: str
    bucket: datetime
    volatility: float
    threshold: float

    @classmethod
    def from_alert(cls, alert: Alert) -> "AlertOut":
        return cls(
            symbol=alert.symbol,
            bucket=alert.bucket,
            volatility=alert.volatility,
            threshold=alert.threshold,
        )
