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


def get_settings() -> Settings:
    return Settings()
