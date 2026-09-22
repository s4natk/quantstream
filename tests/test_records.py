from datetime import datetime, timezone
from types import SimpleNamespace

from quantstream.models import Alert
from quantstream.records import alert_from_row, alert_values, candle_from_row, candle_values
from tests.support import make_candle


def test_candle_values_copy_the_bar():
    candle = make_candle(close=101.5, minute=3)
    values = candle_values(candle)
    assert values["close"] == 101.5
    assert values["symbol"] == "AAPL"
    assert values["trade_count"] == 1
    assert values["bucket"] == candle.bucket


def test_alert_values_copy_the_reading():
    bucket = datetime(2026, 9, 21, 14, 0, tzinfo=timezone.utc)
    alert = Alert("IBM", bucket, 0.04, 0.02)
    assert alert_values(alert) == {
        "symbol": "IBM",
        "bucket": bucket,
        "volatility": 0.04,
        "threshold": 0.02,
    }


def test_candle_from_row_rebuilds_the_bar():
    candle = make_candle(close=88.0, minute=1)
    row = SimpleNamespace(**candle_values(candle))
    assert candle_from_row(row) == candle


def test_alert_from_row_rebuilds_the_reading():
    bucket = datetime(2026, 9, 21, 14, 4, tzinfo=timezone.utc)
    alert = Alert("IBM", bucket, 0.05, 0.02)
    row = SimpleNamespace(**alert_values(alert))
    assert alert_from_row(row) == alert
