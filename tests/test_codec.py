from datetime import datetime, timezone

from quantstream.codec import alert_from_fields, alert_to_fields, candle_from_fields, candle_to_fields
from quantstream.models import Alert
from tests.support import make_candle


def test_candle_round_trips_through_fields():
    candle = make_candle(close=101.25, minute=2)
    restored = candle_from_fields(candle_to_fields(candle))
    assert restored == candle


def test_alert_round_trips_through_fields():
    alert = Alert("IBM", datetime(2026, 9, 21, 14, 2, tzinfo=timezone.utc), 0.041, 0.02)
    assert alert_from_fields(alert_to_fields(alert)) == alert
