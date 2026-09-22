from datetime import datetime, timezone

import pytest
from tests.support import make_candle

from quantstream.codec import (
    CandleDecodeError,
    alert_from_fields,
    alert_to_fields,
    candle_from_fields,
    candle_to_fields,
)
from quantstream.models import Alert


def test_candle_round_trips_through_fields():
    candle = make_candle(close=101.25, minute=2)
    restored = candle_from_fields(candle_to_fields(candle))
    assert restored == candle


def test_alert_round_trips_through_fields():
    alert = Alert("IBM", datetime(2026, 9, 21, 14, 2, tzinfo=timezone.utc), 0.041, 0.02)
    assert alert_from_fields(alert_to_fields(alert)) == alert


def test_missing_candle_close_is_rejected():
    fields = candle_to_fields(make_candle())
    fields["close"] = ""
    with pytest.raises(CandleDecodeError):
        candle_from_fields(fields)
