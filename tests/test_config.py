from quantstream.config import Settings


def test_defaults_point_at_local_services():
    settings = Settings(_env_file=None)
    assert settings.stream_key == "ticks"
    assert settings.candle_interval_seconds == 60
    assert "localhost:5432" in settings.database_url
    assert settings.redis_url.startswith("redis://")
