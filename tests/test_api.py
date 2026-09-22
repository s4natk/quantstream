from datetime import datetime, timezone

from fastapi.testclient import TestClient

from quantstream.api import create_app
from quantstream.models import Alert
from tests.support import make_candle


class StubReader:
    def __init__(self):
        self.calls = []

    async def candles(self, symbol: str):
        self.calls.append(("candles", symbol))
        return [make_candle(close=101.0)]

    async def alerts(self, symbol: str):
        self.calls.append(("alerts", symbol))
        bucket = datetime(2026, 9, 21, 14, 0, tzinfo=timezone.utc)
        return [Alert(symbol, bucket, 0.04, 0.02)]


def test_health_route_is_ok():
    with TestClient(create_app(StubReader())) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_candle_and_alert_routes():
    reader = StubReader()
    with TestClient(create_app(reader)) as client:
        candles = client.get("/candles/aapl")
        alerts = client.get("/alerts/aapl")
    assert candles.status_code == 200
    assert candles.json()[0]["close"] == 101.0
    assert candles.json()[0]["symbol"] == "AAPL"
    assert alerts.status_code == 200
    assert alerts.json()[0]["volatility"] == 0.04
    assert reader.calls == [("candles", "aapl"), ("alerts", "aapl")]
