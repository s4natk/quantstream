from quantstream.session import make_engine


async def test_engine_points_at_the_given_host():
    engine = make_engine("postgresql+asyncpg://quantstream:quantstream@localhost:5432/quantstream")
    try:
        assert engine.url.host == "localhost"
        assert engine.url.database == "quantstream"
    finally:
        await engine.dispose()
