from sqlalchemy.dialects import postgresql

from quantstream.queries import recent_alerts_stmt, recent_candles_stmt, upsert_candle_stmt
from tests.support import make_candle


def test_upsert_targets_the_symbol_bucket_constraint():
    statement = upsert_candle_stmt(make_candle())
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "uq_candles_symbol_bucket" in sql
    assert "ON CONFLICT" in sql


def test_recent_candles_filter_and_sort():
    statement = recent_candles_stmt("AAPL", 10)
    sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
    lowered = sql.lower()
    assert "aapl" in lowered
    assert "order by" in lowered
    assert "desc" in lowered
    assert "10" in lowered


def test_recent_alerts_filter_by_symbol():
    statement = recent_alerts_stmt("IBM", 5)
    lowered = str(statement.compile(compile_kwargs={"literal_binds": True})).lower()
    assert "ibm" in lowered
    assert "alerts" in lowered
    assert "5" in lowered
