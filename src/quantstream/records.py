from quantstream.models import Alert, Candle


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


def alert_values(alert: Alert) -> dict:
    return {
        "symbol": alert.symbol,
        "bucket": alert.bucket,
        "volatility": alert.volatility,
        "threshold": alert.threshold,
    }
