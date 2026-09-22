from datetime import datetime, timezone

from tests.support import make_tick

from quantstream.config import Settings
from quantstream.pipeline import Pipeline
from quantstream.stream import tick_to_fields


def test_tick_inside_the_current_bucket_stays_open():
    pipeline = Pipeline(60, 3, 0.02)
    now = datetime(2026, 9, 21, 14, 0, 40, tzinfo=timezone.utc)
    outcome = pipeline.on_tick(make_tick(second=10), now)
    assert outcome.closed == []
    assert outcome.alerts == []
    assert len(pipeline.builder.open_candles()) == 1


def test_tick_in_a_finished_bucket_is_closed():
    pipeline = Pipeline(60, 3, 0.02)
    now = datetime(2026, 9, 21, 14, 1, tzinfo=timezone.utc)
    outcome = pipeline.on_tick(make_tick(minute=0, price=77.0, size=6), now)
    assert len(outcome.closed) == 1
    assert outcome.closed[0].close == 77.0
    assert outcome.closed[0].volume == 6
    assert pipeline.builder.open_candles() == []


def test_flat_closes_do_not_alert():
    pipeline = Pipeline(60, 3, 0.02)
    now = datetime(2026, 9, 21, 15, 0, tzinfo=timezone.utc)
    alerts = []
    for minute in range(3):
        outcome = pipeline.on_tick(make_tick(minute=minute, price=100.0), now)
        alerts.extend(outcome.alerts)
    assert alerts == []


def test_loud_closes_raise_an_alert():
    pipeline = Pipeline(60, 3, 0.02)
    now = datetime(2026, 9, 21, 15, 0, tzinfo=timezone.utc)
    last = None
    for minute, price in enumerate([100.0, 140.0, 70.0]):
        last = pipeline.on_tick(make_tick(minute=minute, price=price), now)
    assert last is not None
    assert last.alerts
    assert last.alerts[0].volatility >= 0.02
    assert last.alerts[0].symbol == "AAPL"


def test_counters_follow_closed_buckets():
    pipeline = Pipeline(60, 3, 0.02)
    now = datetime(2026, 9, 21, 14, 2, tzinfo=timezone.utc)
    pipeline.on_tick(make_tick(minute=0), now)
    pipeline.on_tick(make_tick(minute=1), now)
    assert pipeline.counters.ticks == 2
    assert pipeline.counters.candles == 2
    assert pipeline.counters.alerts == 0


def test_bad_fields_do_not_become_ticks():
    pipeline = Pipeline(60, 3, 0.02)
    now = datetime(2026, 9, 21, 14, 5, tzinfo=timezone.utc)
    outcome = pipeline.on_fields("8-0", {"symbol": "AAPL"}, now)
    assert outcome.closed == []
    assert outcome.failed[0][0] == "8-0"
    assert pipeline.counters.failed == 1
    assert pipeline.counters.ticks == 0


def test_batch_keeps_good_ticks_and_bad_fields():
    pipeline = Pipeline(60, 3, 0.02)
    now = datetime(2026, 9, 21, 14, 5, tzinfo=timezone.utc)
    tick = make_tick(minute=0, price=50.0)
    outcome = pipeline.on_batch(
        [
            ("1-0", tick_to_fields(tick)),
            ("1-1", {"price": "nope"}),
        ],
        now,
    )
    assert len(outcome.closed) == 1
    assert outcome.closed[0].close == 50.0
    assert len(outcome.failed) == 1


def test_from_settings_uses_the_configured_window():
    settings = Settings(_env_file=None)
    pipeline = Pipeline.from_settings(settings)
    assert pipeline.builder.interval_seconds == settings.candle_interval_seconds
    assert pipeline.tracker.window == settings.volatility_window
    assert pipeline.tracker.threshold == settings.volatility_threshold


def test_symbols_are_stripped_and_uppercased():
    pipeline = Pipeline(60, 3, 0.02)
    now = datetime(2026, 9, 21, 14, 1, tzinfo=timezone.utc)
    outcome = pipeline.on_tick(make_tick(symbol=" msft ", minute=0), now)
    assert outcome.closed[0].symbol == "MSFT"
