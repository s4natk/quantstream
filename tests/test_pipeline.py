from datetime import datetime, timezone

from quantstream.pipeline import Pipeline
from tests.support import make_tick


def test_tick_inside_the_current_bucket_stays_open():
    pipeline = Pipeline(60, 3, 0.02)
    now = datetime(2026, 9, 21, 14, 0, 40, tzinfo=timezone.utc)
    outcome = pipeline.on_tick(make_tick(second=10), now)
    assert outcome.closed == []
    assert outcome.alerts == []
    assert len(pipeline.builder.open_candles()) == 1
