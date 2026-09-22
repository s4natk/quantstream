from pathlib import Path


def test_schema_creates_candles_and_alerts():
    sql = (Path(__file__).resolve().parents[1] / "sql" / "schema.sql").read_text(encoding="utf-8")
    lowered = sql.lower()
    assert "create table if not exists candles" in lowered
    assert "create table if not exists alerts" in lowered
    assert "uq_candles_symbol_bucket" in lowered
    assert "ix_alerts_symbol" in lowered
