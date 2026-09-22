from datetime import datetime, timezone

from quantstream.candles import CandleBuilder
from quantstream.models import Tick


def test_current_bucket_is_not_drained():
    builder = CandleBuilder(60)
    builder.add(Tick("AAPL", 100.0, 1.0, datetime(2026, 9, 21, 14, 0, 10, tzinfo=timezone.utc)))
    now = datetime(2026, 9, 21, 14, 0, 50, tzinfo=timezone.utc)
    assert builder.drain(now) == []


def test_previous_bucket_is_drained_once():
    builder = CandleBuilder(60)
    builder.add(Tick("AAPL", 101.0, 4.0, datetime(2026, 9, 21, 14, 0, 10, tzinfo=timezone.utc)))
    now = datetime(2026, 9, 21, 14, 1, tzinfo=timezone.utc)
    drained = builder.drain(now)
    assert len(drained) == 1
    assert drained[0].close == 101.0
    assert drained[0].volume == 4.0
    assert builder.drain(now) == []
