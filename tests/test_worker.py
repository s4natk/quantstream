from datetime import datetime, timezone

from quantstream.config import Settings
from quantstream.models import Alert
from quantstream.pipeline import Outcome, Pipeline
from quantstream.stream import tick_to_fields
from quantstream.worker import persist_outcome, process_once, run_batches
from tests.fakes import FakeRedis, FakeSession, SessionBox
from tests.support import make_candle, make_tick


def _now() -> datetime:
    return datetime(2026, 9, 21, 14, 2, tzinfo=timezone.utc)


async def test_persist_outcome_writes_and_commits():
    session = FakeSession()
    candle = make_candle(close=42.0)
    alert = Alert(candle.symbol, candle.bucket, 0.04, 0.02)
    await persist_outcome(session, Outcome([candle], [alert]))
    assert session.statements
    assert session.added[0].symbol == "AAPL"
    assert session.committed is True


async def test_process_once_writes_a_closed_candle_and_acks():
    tick = make_tick(minute=0, price=42.0, size=2)
    client = FakeRedis()
    client.reply = [("ticks", [("7-0", tick_to_fields(tick))])]
    session = FakeSession()
    pipeline = Pipeline(60, 3, 0.02)
    outcome = await process_once(
        client,
        SessionBox(session),
        pipeline,
        Settings(_env_file=None),
        _now(),
    )
    assert len(outcome.closed) == 1
    assert outcome.closed[0].close == 42.0
    assert session.committed is True
    assert client.calls[-1][0] == "xack"
    assert client.calls[-1][3] == ("7-0",)


async def test_bad_entries_are_acked_without_a_write():
    client = FakeRedis()
    client.reply = [("ticks", [("1-0", {"symbol": "AAPL"})])]
    session = FakeSession()
    outcome = await process_once(
        client,
        SessionBox(session),
        Pipeline(60, 3, 0.02),
        Settings(_env_file=None),
        _now(),
    )
    assert outcome.failed
    assert session.committed is False
    assert client.calls[-1][0] == "xack"


async def test_run_batches_creates_the_group_and_repeats():
    client = FakeRedis()
    client.reply = []
    results = await run_batches(
        client,
        SessionBox(),
        Pipeline(60, 3, 0.02),
        Settings(_env_file=None),
        _now(),
        2,
    )
    assert len(results) == 2
    assert client.calls[0][0] == "xgroup"
