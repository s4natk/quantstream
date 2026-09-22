from quantstream.models import Alert
from quantstream.pipeline import Outcome
from quantstream.worker import persist_outcome
from tests.fakes import FakeSession
from tests.support import make_candle


async def test_persist_outcome_writes_and_commits():
    session = FakeSession()
    candle = make_candle(close=42.0)
    alert = Alert(candle.symbol, candle.bucket, 0.04, 0.02)
    await persist_outcome(session, Outcome([candle], [alert]))
    assert session.statements
    assert session.added[0].symbol == "AAPL"
    assert session.committed is True
