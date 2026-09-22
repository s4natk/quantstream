from sqlalchemy.dialects import postgresql

from quantstream.queries import upsert_candle_stmt
from tests.support import make_candle


def test_upsert_targets_the_symbol_bucket_constraint():
    statement = upsert_candle_stmt(make_candle())
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "uq_candles_symbol_bucket" in sql
    assert "ON CONFLICT" in sql
