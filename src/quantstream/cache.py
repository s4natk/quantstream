import time


class TtlCache:
    def __init__(self, ttl_seconds: float, now=None) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl must be positive")
        self.ttl_seconds = ttl_seconds
        self._now = now or time.monotonic
        self._stored: dict[str, tuple[float, object]] = {}

    def get(self, key: str):
        found = self._stored.get(key)
        if found is None:
            return None
        saved, value = found
        if self._now() - saved >= self.ttl_seconds:
            self._stored.pop(key, None)
            return None
        return value

    def put(self, key: str, value) -> None:
        self._stored[key] = (self._now(), value)
