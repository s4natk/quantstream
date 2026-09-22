from datetime import datetime, timezone

from quantstream.candles import CandleBuilder
from quantstream.models import Tick


def test_current_bucket_is_not_drained():
    builder = CandleBuilder(60)
    builder.add(Tick("AAPL", 100.0, 1.0, datetime(2026, 9, 21, 14, 0, 10, tzinfo=timezone.utc)))
    now = datetime(2026, 9, 21, 14, 0, 50, tzinfo=timezone.utc)
    assert builder.drain(now) == []
