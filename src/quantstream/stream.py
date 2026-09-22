from datetime import datetime, timezone

from quantstream.models import Tick


def tick_to_fields(tick: Tick) -> dict[str, str]:
    ts = tick.ts if tick.ts.tzinfo else tick.ts.replace(tzinfo=timezone.utc)
    return {
        "symbol": tick.symbol,
        "price": f"{tick.price:.8f}",
        "size": f"{tick.size:.8f}",
        "ts": ts.isoformat(),
    }


def tick_from_fields(fields: dict[str, str]) -> Tick:
    ts = datetime.fromisoformat(fields["ts"])
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return Tick(
        symbol=fields["symbol"],
        price=float(fields["price"]),
        size=float(fields["size"]),
        ts=ts,
    )
