from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel

from quantstream.models import Alert, Candle
from quantstream.reader import CandleReader


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


def create_app(reader: CandleReader) -> FastAPI:
    app = FastAPI(title="QuantStream")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/candles/{symbol}", response_model=list[CandleOut])
    async def candles(symbol: str) -> list[CandleOut]:
        rows = await reader.candles(symbol)
        return [CandleOut.from_candle(row) for row in rows]

    @app.get("/alerts/{symbol}", response_model=list[AlertOut])
    async def alerts(symbol: str) -> list[AlertOut]:
        rows = await reader.alerts(symbol)
        return [AlertOut.from_alert(row) for row in rows]

    return app
