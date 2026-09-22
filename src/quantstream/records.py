from quantstream.models import Candle


def candle_values(candle: Candle) -> dict:
    return {
        "symbol": candle.symbol,
        "bucket": candle.bucket,
        "open": candle.open,
        "high": candle.high,
        "low": candle.low,
        "close": candle.close,
        "volume": candle.volume,
        "trade_count": candle.trade_count,
    }
