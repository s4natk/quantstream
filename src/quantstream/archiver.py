import asyncio
from datetime import datetime, timezone
from pathlib import Path

from quantstream.archive import export_candles
from quantstream.config import get_settings
from quantstream.object_store import make_s3, store_exports
from quantstream.session import make_engine, make_session_factory
from quantstream.storage import load_candles_before


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def export_once(sessions, directory: Path, before: datetime, limit: int) -> list[Path]:
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    async with sessions() as session:
        candles = await load_candles_before(session, before, limit)
    return export_candles(path, candles)


async def serve() -> None:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    sessions = make_session_factory(engine)
    try:
        while True:
            written = await export_once(
                sessions,
                Path(settings.archive_dir),
                utcnow(),
                settings.archive_batch,
            )
            if settings.archive_bucket:
                store_exports(
                    make_s3(),
                    settings.archive_bucket,
                    settings.archive_prefix,
                    written,
                )
            await asyncio.sleep(settings.archive_interval_seconds)
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    main()
