from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://quantstream:quantstream@localhost:5432/quantstream"
    )
    redis_url: str = "redis://localhost:6379/0"
    stream_key: str = "ticks"
    candle_interval_seconds: int = 60
    volatility_window: int = 20
    volatility_threshold: float = 0.02
    cache_ttl_seconds: int = 5
    consumer_group: str = "candles"
    consumer_name: str = "worker-1"
    stream_block_ms: int = 2000
    stream_read_count: int = 200
    feed_url: str = "ws://localhost:8765/trades"
    feed_symbols: str = "AAPL,MSFT"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    query_limit: int = 200
    archive_dir: str = "archives"
    archive_batch: int = 5000
    archive_interval_seconds: int = 60
    archive_bucket: str = ""
    archive_prefix: str = "candles"

    def symbol_list(self) -> list[str]:
        names = []
        for part in self.feed_symbols.split(","):
            name = part.strip().upper()
            if name:
                names.append(name)
        return names


def get_settings() -> Settings:
    return Settings()
