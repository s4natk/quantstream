from datetime import datetime, timezone

import pytest

from quantstream.feed import TradeParseError, parse_trade


def test_parse_trade_uppercases_symbol_and_reads_time():
    payload = '{"symbol": "aapl", "price": 190.25, "size": 10, "ts": "2026-09-22T14:00:01+00:00"}'
    tick = parse_trade(payload)
    assert tick.symbol == "AAPL"
    assert tick.price == 190.25
    assert tick.size == 10
    assert tick.ts == datetime(2026, 9, 22, 14, 0, 1, tzinfo=timezone.utc)


def test_bad_trade_payload_is_rejected():
    with pytest.raises(TradeParseError):
        parse_trade("not-json")
    with pytest.raises(TradeParseError):
        parse_trade('{"symbol": "AAPL", "price": 0, "size": 1, "ts": "2026-09-22T14:00:01+00:00"}')
