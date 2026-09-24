from datetime import timedelta
from types import SimpleNamespace

from quantstream.archive import export_candles, read_candles, write_candles
from quantstream.archiver import export_once
from tests.fakes import FakeSession, SessionBox
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


def test_export_splits_days_and_replaces_the_same_bar(tmp_path):
    first = make_candle(close=100.0)
    later = make_candle(close=105.0)
    other_day = make_candle(symbol="MSFT", close=40.0, minute=600)
    written = export_candles(tmp_path, [first, other_day])
    assert [path.name for path in written] == ["2026-09-21.parquet", "2026-09-22.parquet"]
    export_candles(tmp_path, [later, make_candle(symbol="MSFT", close=41.0)])
    day = read_candles(tmp_path / "2026-09-21.parquet")
    assert [(candle.symbol, candle.close) for candle in day] == [("AAPL", 105.0), ("MSFT", 41.0)]


async def test_export_once_writes_rows_from_the_session(tmp_path):
    candle = make_candle(close=11.0)
    row = SimpleNamespace(
        symbol=candle.symbol,
        bucket=candle.bucket,
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
        trade_count=candle.trade_count,
    )
    written = await export_once(
        SessionBox(FakeSession(rows=[row])),
        tmp_path,
        candle.bucket + timedelta(minutes=1),
        10,
    )
    assert read_candles(written[0]) == [candle]
