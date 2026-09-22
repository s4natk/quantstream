import pytest

from quantstream.cache import TtlCache


def test_value_expires_when_the_ttl_elapses():
    clock = {"now": 0.0}
    cache = TtlCache(5, now=lambda: clock["now"])
    cache.put("candles:AAPL", ["bar"])
    assert cache.get("candles:AAPL") == ["bar"]
    clock["now"] = 5.0
    assert cache.get("candles:AAPL") is None


def test_ttl_must_be_positive():
    with pytest.raises(ValueError):
        TtlCache(0)
