from quantstream.cache import TtlCache
from quantstream.models import Alert, Candle
from quantstream.storage import load_recent_alerts, load_recent_candles


class CandleReader:
    def __init__(self, sessions, cache: TtlCache, limit: int) -> None:
        self.sessions = sessions
        self.cache = cache
        self.limit = limit

    async def candles(self, symbol: str) -> list[Candle]:
        name = symbol.strip().upper()
        key = f"candles:{name}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        async with self.sessions() as session:
            rows = await load_recent_candles(session, name, self.limit)
        self.cache.put(key, rows)
        return rows

    async def alerts(self, symbol: str) -> list[Alert]:
        name = symbol.strip().upper()
        key = f"alerts:{name}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        async with self.sessions() as session:
            rows = await load_recent_alerts(session, name, self.limit)
        self.cache.put(key, rows)
        return rows
