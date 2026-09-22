from datetime import datetime, timezone

from quantstream.models import Candle


class CandleDecodeError(ValueError):
    pass


def candle_to_fields(candle: Candle) -> dict[str, str]:
    bucket = candle.bucket
    if bucket.tzinfo is None:
        bucket = bucket.replace(tzinfo=timezone.utc)
    return {
        "symbol": candle.symbol,
        "bucket": bucket.isoformat(),
        "open": f"{candle.open:.8f}",
        "high": f"{candle.high:.8f}",
        "low": f"{candle.low:.8f}",
        "close": f"{candle.close:.8f}",
        "volume": f"{candle.volume:.8f}",
        "trade_count": str(candle.trade_count),
    }


def candle_from_fields(fields: dict[str, str]) -> Candle:
    required = ("symbol", "bucket", "open", "high", "low", "close", "volume", "trade_count")
    missing = [key for key in required if fields.get(key) in (None, "")]
    if missing:
        raise CandleDecodeError("missing " + ", ".join(missing))
    try:
        bucket = datetime.fromisoformat(fields["bucket"])
        trade_count = int(fields["trade_count"])
        numbers = {key: float(fields[key]) for key in ("open", "high", "low", "close", "volume")}
    except ValueError as exc:
        raise CandleDecodeError("candle fields are not valid") from exc
    if bucket.tzinfo is None:
        bucket = bucket.replace(tzinfo=timezone.utc)
    return Candle(
        symbol=fields["symbol"],
        bucket=bucket,
        open=numbers["open"],
        high=numbers["high"],
        low=numbers["low"],
        close=numbers["close"],
        volume=numbers["volume"],
        trade_count=trade_count,
    )
