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


def candle_from_row(row) -> Candle:
    return Candle(
        symbol=row.symbol,
        bucket=row.bucket,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
        trade_count=row.trade_count,
    )


def alert_from_row(row) -> Alert:
    return Alert(
        symbol=row.symbol,
        bucket=row.bucket,
        volatility=row.volatility,
        threshold=row.threshold,
    )
