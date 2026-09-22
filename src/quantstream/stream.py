import math
from datetime import datetime, timezone

from quantstream.models import Tick


class TickDecodeError(ValueError):
    pass


def tick_to_fields(tick: Tick) -> dict[str, str]:
    ts = tick.ts if tick.ts.tzinfo else tick.ts.replace(tzinfo=timezone.utc)
    return {
        "symbol": tick.symbol,
        "price": f"{tick.price:.8f}",
        "size": f"{tick.size:.8f}",
        "ts": ts.isoformat(),
    }


def tick_from_fields(fields: dict[str, str]) -> Tick:
    missing = [key for key in ("symbol", "price", "size", "ts") if not fields.get(key)]
    if missing:
        raise TickDecodeError("missing " + ", ".join(missing))
    try:
        price = float(fields["price"])
        size = float(fields["size"])
    except ValueError as exc:
        raise TickDecodeError("price and size must be numbers") from exc
    if not math.isfinite(price) or price <= 0:
        raise TickDecodeError("price must be positive")
    if not math.isfinite(size) or size < 0:
        raise TickDecodeError("size cannot be negative")
    try:
        ts = datetime.fromisoformat(fields["ts"])
    except ValueError as exc:
        raise TickDecodeError("ts is not a timestamp") from exc
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return Tick(symbol=fields["symbol"], price=price, size=size, ts=ts)
