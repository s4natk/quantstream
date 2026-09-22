from datetime import datetime, timedelta, timezone

import pytest

from quantstream.models import Candle
from quantstream.volatility import VolatilityTracker, realized_vol


def _candle(minute: int, close: float) -> Candle:
    bucket = datetime(2026, 9, 21, 14, 0, tzinfo=timezone.utc) + timedelta(minutes=minute)
    return Candle("AAPL", bucket, close, close, close, close, 1.0, 1)


def test_flat_closes_have_no_volatility():
    assert realized_vol([100.0, 100.0, 100.0, 100.0]) == 0.0


def test_short_window_returns_none():
    assert realized_vol([100.0, 101.0]) is None


def test_tracker_alerts_when_window_is_loud():
    tracker = VolatilityTracker(window=6, threshold=0.02)
    quiet = [_candle(i, 100.0) for i in range(3)]
    loud = [
        _candle(3, 120.0),
        _candle(4, 80.0),
        _candle(5, 130.0),
    ]
    assert all(tracker.observe(candle) is None for candle in quiet)
    for candle in loud[:-1]:
        tracker.observe(candle)
    alert = tracker.observe(loud[-1])
    assert alert is not None
    assert alert.symbol == "AAPL"
    assert alert.volatility >= alert.threshold


def test_window_keeps_only_the_newest_closes():
    tracker = VolatilityTracker(window=3, threshold=0.02)
    for minute, price in enumerate([10.0, 11.0, 12.0, 13.0]):
        tracker.observe(_candle(minute, price))
    assert tracker.closes("AAPL") == [11.0, 12.0, 13.0]


def test_symbols_do_not_share_a_window():
    tracker = VolatilityTracker(window=3, threshold=0.02)
    loud = [100.0, 150.0, 60.0]
    alert = None
    for minute, price in enumerate(loud):
        bucket = _candle(minute, price).bucket
        assert tracker.observe(_candle(minute, 100.0)) is None
        alert = tracker.observe(Candle("MSFT", bucket, price, price, price, price, 1.0, 1))
    assert alert is not None
    assert alert.symbol == "MSFT"


def test_matching_threshold_still_alerts():
    prices = [100.0, 110.0, 90.0, 120.0]
    vol = realized_vol(prices)
    assert vol is not None and vol > 0
    tracker = VolatilityTracker(window=4, threshold=vol)
    alert = None
    for minute, price in enumerate(prices):
        alert = tracker.observe(_candle(minute, price))
    assert alert is not None
    assert alert.volatility == vol


def test_reading_is_empty_until_three_closes():
    tracker = VolatilityTracker(window=4, threshold=0.02)
    assert tracker.reading("AAPL") is None
    tracker.observe(_candle(0, 100.0))
    tracker.observe(_candle(1, 100.0))
    assert tracker.reading("AAPL") is None
    tracker.observe(_candle(2, 100.0))
    assert tracker.reading("AAPL") == 0.0


def test_non_positive_prices_have_no_volatility():
    assert realized_vol([100.0, 0.0, 101.0, 102.0]) is None
    assert realized_vol([100.0, -2.0, 101.0, 99.0]) is None


def test_window_must_cover_three_closes():
    with pytest.raises(ValueError):
        VolatilityTracker(window=2, threshold=0.02)


def test_threshold_must_be_positive():
    with pytest.raises(ValueError):
        VolatilityTracker(window=3, threshold=0)
