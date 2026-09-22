from datetime import datetime, timezone

from quantstream.candles import CandleBuilder, bucket_start
from quantstream.models import Tick


def _tick(second: int, price: float, size: float = 10.0) -> Tick:
    return Tick("AAPL", price, size, datetime(2026, 9, 21, 14, 0, second, tzinfo=timezone.utc))


def test_bucket_aligns_to_interval():
    ts = datetime(2026, 9, 21, 14, 0, 47, tzinfo=timezone.utc)
    assert bucket_start(ts, 60) == datetime(2026, 9, 21, 14, 0, tzinfo=timezone.utc)


def test_builder_folds_ticks_into_one_bar():
    builder = CandleBuilder(60)
    first = builder.add(_tick(1, 100.0, 5))
    second = builder.add(_tick(20, 103.0, 7))
    third = builder.add(_tick(40, 99.0, 3))
    assert first.open == 100.0
    assert third.open == 100.0
    assert third.high == 103.0
    assert third.low == 99.0
    assert third.close == 99.0
    assert third.volume == 15.0
    assert third.trade_count == 3
    assert second.bucket == third.bucket


def test_builder_keeps_separate_buckets():
    builder = CandleBuilder(60)
    builder.add(_tick(10, 100.0))
    later = Tick("AAPL", 110.0, 1.0, datetime(2026, 9, 21, 14, 1, 5, tzinfo=timezone.utc))
    candle = builder.add(later)
    assert candle.open == 110.0
    assert candle.trade_count == 1
    assert candle.bucket == datetime(2026, 9, 21, 14, 1, tzinfo=timezone.utc)


def test_five_second_bucket_aligns_down():
    ts = datetime(2026, 9, 21, 14, 0, 47, tzinfo=timezone.utc)
    assert bucket_start(ts, 5) == datetime(2026, 9, 21, 14, 0, 45, tzinfo=timezone.utc)
