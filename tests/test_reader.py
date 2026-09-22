from types import SimpleNamespace

from quantstream.cache import TtlCache
from quantstream.reader import CandleReader
from tests.fakes import FakeSession, SessionBox
from tests.support import make_candle


def _row(candle):
    return SimpleNamespace(
        symbol=candle.symbol,
        bucket=candle.bucket,
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
        trade_count=candle.trade_count,
    )


async def test_second_candle_read_uses_the_cache():
    candle = make_candle(close=101.5)
    session = FakeSession(rows=[_row(candle)])
    reader = CandleReader(SessionBox(session), TtlCache(5, now=lambda: 0.0), 10)
    first = await reader.candles("aapl")
    second = await reader.candles("AAPL")
    assert first[0].close == 101.5
    assert second[0].symbol == "AAPL"
    assert len(session.statements) == 1


async def test_alert_read_is_cached_separately():
    candle = make_candle()
    alert_row = SimpleNamespace(
        symbol="AAPL",
        bucket=candle.bucket,
        volatility=0.05,
        threshold=0.02,
    )
    session = FakeSession(rows=[alert_row])
    reader = CandleReader(SessionBox(session), TtlCache(5, now=lambda: 0.0), 10)
    first = await reader.alerts("AAPL")
    second = await reader.alerts("AAPL")
    assert first[0].volatility == 0.05
    assert second[0].threshold == 0.02
    assert len(session.statements) == 1
