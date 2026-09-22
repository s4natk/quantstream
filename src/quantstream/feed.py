import json
import math
from datetime import datetime, timezone

from quantstream.models import Tick


class TradeParseError(ValueError):
    pass


def parse_trade(payload: str) -> Tick:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise TradeParseError("payload is not json") from exc
    if not isinstance(data, dict):
        raise TradeParseError("payload must be an object")
    try:
        symbol = str(data["symbol"]).strip().upper()
        price = float(data["price"])
        size = float(data["size"])
        ts = datetime.fromisoformat(str(data["ts"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise TradeParseError("trade fields are not valid") from exc
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    if not symbol or not math.isfinite(price) or price <= 0:
        raise TradeParseError("trade fields are not valid")
    if not math.isfinite(size) or size < 0:
        raise TradeParseError("trade fields are not valid")
    return Tick(symbol, price, size, ts)
