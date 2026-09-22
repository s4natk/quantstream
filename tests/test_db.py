from quantstream.db import AlertRow, Base, CandleRow


def test_metadata_registers_candles_and_alerts():
    assert set(Base.metadata.tables) == {"candles", "alerts"}


def test_candle_rows_are_unique_per_symbol_and_bucket():
    columns = {column.name for column in CandleRow.__table__.columns}
    assert {"symbol", "bucket", "open", "high", "low", "close", "volume", "trade_count"} <= columns
    names = {constraint.name for constraint in CandleRow.__table__.constraints}
    assert "uq_candles_symbol_bucket" in names


def test_alerts_are_indexed_by_symbol():
    indexed = [column.name for index in AlertRow.__table__.indexes for column in index.columns]
    assert "symbol" in indexed
