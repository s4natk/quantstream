from datetime import datetime, timezone

from quantstream.models import Alert, Candle, Tick


def test_tick_keeps_price_and_size():
    tick = Tick("AAPL", 190.25, 100.0, datetime(2026, 9, 21, tzinfo=timezone.utc))
    assert tick.symbol == "AAPL"
    assert tick.price == 190.25
    assert tick.size == 100.0


def test_candle_and_alert_are_immutable():
    bucket = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
    candle = Candle("AAPL", bucket, 190.0, 191.0, 189.5, 190.5, 1200.0, 8)
    alert = Alert("AAPL", bucket, 0.031, 0.02)
    assert candle.trade_count == 8
    assert alert.volatility > alert.threshold
