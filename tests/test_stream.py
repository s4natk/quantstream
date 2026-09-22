from datetime import datetime, timezone

from quantstream.models import Tick
from quantstream.stream import tick_from_fields, tick_to_fields


def test_tick_round_trips_through_stream_fields():
    tick = Tick("MSFT", 420.5, 25.0, datetime(2026, 9, 21, 15, 4, 12, tzinfo=timezone.utc))
    restored = tick_from_fields(tick_to_fields(tick))
    assert restored.symbol == tick.symbol
    assert restored.price == tick.price
    assert restored.size == tick.size
    assert restored.ts == tick.ts


def test_naive_timestamp_is_treated_as_utc():
    tick = Tick("MSFT", 10.0, 1.0, datetime(2026, 9, 21, 15, 4, 12))
    restored = tick_from_fields(tick_to_fields(tick))
    assert restored.ts.tzinfo == timezone.utc
    assert restored.ts.hour == 15
