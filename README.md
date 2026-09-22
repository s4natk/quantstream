# QuantStream

Live trades land on a Redis stream. A worker folds them into rolling OHLC candles, writes those candles to Postgres, and raises a volatility alert when the recent window gets loud. FastAPI serves the candles and alerts from a short cache.

Four processes:

- ingest reads the websocket and appends ticks
- worker builds candles and alerts
- api serves them
- archiver writes closed candles out as Parquet

Postgres and Redis run locally from Compose. Container images, ECS, RDS, S3, and the GitHub Actions deploy come after the services actually run.

The library underneath that is in place. A tick is stored as Redis stream fields. `Pipeline` folds ticks into an open candle and drains the bucket once its minute has ended. Closed candles go through a rolling volatility check. Candles and alerts then map onto the tables in `sql/schema.sql`.

## Run the services

With Postgres and Redis up, start each process in its own shell:

```bash
python -m quantstream.ingest
python -m quantstream.worker
python -m quantstream.api
```

Ingest reads `FEED_URL` and appends trades to the Redis stream. The worker drains that stream into candles and alerts. The API serves `GET /candles/{symbol}` and `GET /alerts/{symbol}`, and keeps each response for `CACHE_TTL_SECONDS`.

## Run the dependencies

```bash
cp .env.example .env
docker compose up -d
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

On macOS or Linux the activate line is `source .venv/bin/activate`.
