from datetime import datetime, timezone

from quantstream.models import Alert
from quantstream.storage import write_alert, write_candle
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
