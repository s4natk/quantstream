from datetime import datetime, timezone

import pytest

from quantstream.models import Tick
from quantstream.stream import TickDecodeError, tick_from_fields, tick_to_fields


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


def _fields(**overrides):
    base = {
        "symbol": "MSFT",
        "price": "10.00000000",
        "size": "1.00000000",
        "ts": "2026-09-21T15:04:12+00:00",
    }
    base.update(overrides)
    return base


def test_missing_field_is_rejected():
    fields = _fields()
    fields["symbol"] = ""
    with pytest.raises(TickDecodeError):
        tick_from_fields(fields)


def test_non_numeric_price_is_rejected():
    with pytest.raises(TickDecodeError):
        tick_from_fields(_fields(price="abc"))


def test_negative_size_is_rejected():
    with pytest.raises(TickDecodeError):
        tick_from_fields(_fields(size="-1"))
