# QuantStream

Live trades land on a Redis stream. A worker folds them into rolling OHLC candles, writes those candles to Postgres, and raises a volatility alert when the recent window gets loud. FastAPI serves the candles and alerts from a short cache.

Four processes:

- ingest reads the websocket and appends ticks
- worker builds candles and alerts
- api serves them
- archiver writes closed candles out as Parquet

Postgres and Redis run locally from Compose. Container images, ECS, RDS, S3, and the GitHub Actions deploy come after the services actually run.

## Run the dependencies

```bash
cp .env.example .env
docker compose up -d
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

On macOS or Linux the activate line is `source .venv/bin/activate`.
