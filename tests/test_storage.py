from datetime import datetime, timezone
from types import SimpleNamespace

from quantstream.models import Alert
from quantstream.storage import load_recent_alerts, load_recent_candles, write_alert, write_candle
from tests.fakes import FakeSession
from tests.support import make_candle


async def test_writes_execute_upsert_and_stage_alert():
    session = FakeSession()
    candle = make_candle(close=101.0)
    bucket = datetime(2026, 9, 21, 14, 0, tzinfo=timezone.utc)
    alert = Alert(candle.symbol, bucket, 0.03, 0.02)
    await write_candle(session, candle)
    await write_alert(session, alert)
    assert session.statements
    assert session.added[0].symbol == "AAPL"
    assert session.added[0].volatility == 0.03


async def test_loads_map_rows_back_to_models():
    bucket = datetime(2026, 9, 21, 14, 0, tzinfo=timezone.utc)
    candle_row = SimpleNamespace(
        symbol="AAPL",
        bucket=bucket,
        open=1.0,
        high=2.0,
        low=0.5,
        close=1.5,
        volume=3.0,
        trade_count=4,
    )
    alert_row = SimpleNamespace(symbol="AAPL", bucket=bucket, volatility=0.05, threshold=0.02)
    session = FakeSession(rows=[candle_row])
    candles = await load_recent_candles(session, "AAPL", 10)
    assert candles[0].close == 1.5
    assert candles[0].trade_count == 4
    session.rows = [alert_row]
    alerts = await load_recent_alerts(session, "AAPL", 5)
    assert alerts[0].threshold == 0.02
