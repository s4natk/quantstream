from quantstream.records import candle_values
from tests.support import make_candle


def test_candle_values_copy_the_bar():
    candle = make_candle(close=101.5, minute=3)
    values = candle_values(candle)
    assert values["close"] == 101.5
    assert values["symbol"] == "AAPL"
    assert values["trade_count"] == 1
    assert values["bucket"] == candle.bucket
