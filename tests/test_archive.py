from quantstream.archive import read_candles, write_candles
from tests.support import make_candle


def test_candles_round_trip_through_parquet(tmp_path):
    path = tmp_path / "candles.parquet"
    original = [
        make_candle(close=101.5, minute=1),
        make_candle(symbol="MSFT", close=40.0, minute=2),
    ]
    write_candles(path, original)
    assert read_candles(path) == original


def test_empty_archive_is_readable(tmp_path):
    path = tmp_path / "empty.parquet"
    write_candles(path, [])
    assert read_candles(path) == []
