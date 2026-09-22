from tests.support import make_candle
from quantstream.codec import candle_from_fields, candle_to_fields


def test_candle_round_trips_through_fields():
    candle = make_candle(close=101.25, minute=2)
    restored = candle_from_fields(candle_to_fields(candle))
    assert restored == candle
