# QuantStream
### Live trades into rolling OHLC candles and volatility alerts
*Python • FastAPI • PostgreSQL • Redis • Docker • AWS ECS/Fargate • RDS • ElastiCache • S3 • CloudWatch • GitHub Actions*

---

## Overview

QuantStream takes a websocket of trades and turns them into rolling OHLC candles, a volatility alert when a name gets loud, and an HTTP API for both. Closed candles are also written out as Parquet, and to S3 when a bucket is set.

The point of the project is the path from a live print to something you can query: ingest, a Redis stream, a worker that builds candles, Postgres for the rows, and a short cache in front of the API. The same four processes run on a laptop with Docker Compose, or on ECS Fargate from `deploy/stack.yml`.

A separate chart page runs that same candle and volatility code on synthetic AAPL and MSFT prices, so the screen can be opened without Postgres, Redis, or AWS.

---

# System Goals

- Read a websocket of trades and keep only the configured symbols
- Fold each print into an open OHLC candle and close the bucket when its interval ends
- Measure realized volatility on recent closes and store an alert when it crosses the threshold
- Serve recent candles and alerts over HTTP, with a short in-process cache
- Archive closed candles as daily Parquet files, and upload them when `ARCHIVE_BUCKET` is set
- Run ingest, worker, api, and archiver as separate processes locally or as four Fargate services

---

# Run it on your machine

You need Python 3.11 or newer. The chart page needs nothing else. The full pipeline also needs Docker, for Postgres and Redis, and a websocket that sends trades.

## Chart page

From the repo root:

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m quantstream.demo
```

**macOS or Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m quantstream.demo
```

Open http://127.0.0.1:8000. The page polls `/demo/state` once a second and draws 15-second candles for AAPL and MSFT, plus a volume pane and any volatility alerts. Prices are generated in the process. `/health` returns `{"status":"ok"}`.

## Full pipeline

Install Docker Desktop, then from the repo root:

**Windows (PowerShell)**

```powershell
Copy-Item .env.example .env
docker compose up -d postgres redis
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

**macOS or Linux**

```bash
cp .env.example .env
docker compose up -d postgres redis
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Postgres listens on `localhost:5432` and Redis on `localhost:6379`. The worker creates the `candles` and `alerts` tables on startup. `sql/schema.sql` is the same shape, for reading.

`.env.example` is already pointed at those local ports. Defaults that matter:

| Setting | Default | What it does |
| --- | --- | --- |
| `FEED_URL` | `ws://localhost:8765/trades` | Websocket the ingest process reads |
| `FEED_SYMBOLS` | `AAPL,MSFT` | Symbols kept from the feed |
| `CANDLE_INTERVAL_SECONDS` | `60` | How long a candle stays open |
| `VOLATILITY_WINDOW` | `20` | Recent closes used for the vol check |
| `VOLATILITY_THRESHOLD` | `0.02` | Alert when realized vol is at least this |
| `CACHE_TTL_SECONDS` | `5` | How long an API response is reused |
| `ARCHIVE_DIR` | `archives` | Where Parquet files are written |
| `ARCHIVE_BUCKET` | empty | S3 bucket. Empty keeps files local only |

A candle is queryable after its interval closes, so the first `GET /candles/AAPL` is empty until that minute ends. Set `CANDLE_INTERVAL_SECONDS=15` in `.env` if you want the first rows sooner. An alert needs at least three closed candles and realized vol at or above the threshold, so a quiet feed can run for a while with no alerts.

### Trade feed

Ingest expects one JSON object per websocket message:

```json
{"symbol": "AAPL", "price": 190.25, "size": 12.0, "ts": "2026-09-30T18:00:00+00:00"}
```

`price` must be positive, `size` cannot be negative, and `ts` is an ISO timestamp. A missing timezone is treated as UTC. Point `FEED_URL` at any socket that sends that shape, or run this local feed in its own terminal after the install above. It uses the `websockets` package already installed with the project.

```python
import asyncio
import json
import random
from datetime import datetime, timezone

import websockets

async def handler(websocket):
    prices = {"AAPL": 190.0, "MSFT": 420.0}
    while True:
        for symbol, price in list(prices.items()):
            price = round(max(1.0, price + random.uniform(-0.4, 0.4)), 2)
            prices[symbol] = price
            await websocket.send(json.dumps({
                "symbol": symbol,
                "price": price,
                "size": round(random.uniform(1, 40), 2),
                "ts": datetime.now(timezone.utc).isoformat(),
            }))
        await asyncio.sleep(0.2)

async def main():
    async with websockets.serve(handler, "127.0.0.1", 8765):
        await asyncio.Future()

asyncio.run(main())
```

Save it as `feed.py` and run `python feed.py`. Leave it running.

### Start the four processes

Each one in its own terminal, with the virtualenv active and `.env` in the repo root:

```bash
python -m quantstream.ingest
python -m quantstream.worker
python -m quantstream.api
python -m quantstream.archiver
```

- ingest connects to `FEED_URL` and appends ticks to the Redis stream `ticks`
- worker reads that stream as consumer group `candles`, builds candles, and writes candles and alerts to Postgres
- api listens on port 8000
- archiver writes closed candles under `archives/` as Parquet, one file per day, and uploads them when `ARCHIVE_BUCKET` is set

Check it:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/candles/AAPL
curl http://127.0.0.1:8000/alerts/AAPL
```

`/candles/{symbol}` and `/alerts/{symbol}` return the most recent rows, up to `QUERY_LIMIT` (200).

### All four in containers

Postgres, Redis, and the four app containers:

```bash
docker compose up --build
```

The API is on port 8000. Parquet files land in the `archives` volume.

`FEED_URL` inside Compose has to be a socket the ingest container can reach. A feed on the host machine is `ws://host.docker.internal:8765/trades` in `docker-compose.yml`. The file ships with `ws://localhost:8765/trades`, which is the container itself.

### Tests

With the dev extra installed:

```bash
pytest
```

Tests use in-memory stand-ins for Redis, Postgres, and S3. Docker does not have to be running.

---

# Layout

```text
quantstream/
├── src/quantstream/
│   ├── ingest.py            # websocket reader, publishes ticks
│   ├── worker.py            # stream consumer, writes candles and alerts
│   ├── api.py               # FastAPI candles and alerts
│   ├── archiver.py          # Parquet export, optional S3 upload
│   ├── demo.py              # synthetic chart page
│   ├── pipeline.py          # tick to closed candle to alert
│   ├── candles.py           # OHLC buckets
│   ├── volatility.py        # realized vol on recent closes
│   ├── feed.py              # trade JSON parser
│   ├── stream.py            # tick fields on the Redis stream
│   ├── storage.py           # Postgres writes
│   ├── archive.py           # Parquet schema
│   └── object_store.py      # S3 upload
├── sql/schema.sql           # candles and alerts tables
├── deploy/stack.yml         # VPC, RDS, ElastiCache, S3, ECS, ALB
├── .github/workflows/deploy.yml
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env.example
```

---

# How a trade moves

```text
                     WebSocket trade feed
                     {symbol, price, size, ts}
                                    |
                                    v
                     ┌─────────────────────────────┐
                     │            ingest            │
                     │   keeps FEED_SYMBOLS only    │
                     └──────────────┬──────────────┘
                                    | Redis stream "ticks"
                                    v
                     ┌─────────────────────────────┐
                     │            worker            │
                     │  OHLC candle + vol check     │
                     └──────────────┬──────────────┘
                                    |
                 ┌──────────────────┴──────────────────┐
                 v                                     v
      ┌─────────────────────┐               ┌─────────────────────┐
      │ Postgres            │               │ archiver            │
      │ candles, alerts     │──────────────▶│ Parquet, then S3    │
      └──────────┬──────────┘               └─────────────────────┘
                 |
                 v
      ┌─────────────────────┐
      │ api                 │
      │ 5s response cache   │
      │ /candles  /alerts   │
      └─────────────────────┘
```

The chart page skips this path. It feeds synthetic prints straight into `Pipeline` and serves the HTML itself.

---

## 1. Ingest

- Connects to `FEED_URL` with the `websockets` client
- Parses each message as a trade. Bad JSON is dropped
- Drops symbols that are not in `FEED_SYMBOLS`
- Appends each kept tick to the Redis stream as `symbol`, `price`, `size`, and `ts`

## 2. Worker

- Ensures the Redis consumer group `candles`
- Reads batches and folds them through `Pipeline`
- Builds one open candle per symbol and interval. A tick updates high, low, close, volume, and trade count. The bucket closes once `now` is past the end of the interval
- On each closed candle, computes realized volatility from the log returns of recent closes. The window default is 20. Fewer than three closes produces no reading
- Writes an alert when that vol is at least `VOLATILITY_THRESHOLD` (default `0.02`)
- Upserts candles on `(symbol, bucket)` and inserts alerts
- Acks the stream entries after the batch

## 3. API

- `GET /health`
- `GET /candles/{symbol}` returns recent OHLC rows: bucket, open, high, low, close, volume, trade count
- `GET /alerts/{symbol}` returns symbol, bucket, volatility, and threshold
- Reads Postgres through SQLAlchemy and asyncpg
- Keeps each response in a process-local TTL cache for `CACHE_TTL_SECONDS` (default 5)

## 4. Archiver

- Loads closed candles whose bucket is before now, in batches of `ARCHIVE_BATCH` (default 5000)
- Writes one Parquet file per day under `ARCHIVE_DIR`
- Sleeps `ARCHIVE_INTERVAL_SECONDS` (default 60) between passes
- When `ARCHIVE_BUCKET` is set, uploads those files under `ARCHIVE_PREFIX` (default `candles`)

## 5. Chart page

- One process, `python -m quantstream.demo`
- Seeds about 20 minutes of 15-second bars, then keeps printing
- Uses the same `Pipeline` as the worker, with a window of 5 and the same `0.02` threshold
- Serves the candlestick screen on `/`, the latest bars on `/demo/state`, and `/health`

---

# Cloud layout

`deploy/stack.yml` is the CloudFormation template for the same four processes on AWS.

```text
                     ┌─────────────────────────────┐
                     │     Application Load Balancer│
                     │           HTTP :80           │
                     └──────────────┬──────────────┘
                                    | /health on :8000
                                    v
                     ┌─────────────────────────────┐
                     │   ECS Fargate: api          │
                     └──────────────┬──────────────┘
                                    |
         ┌──────────────────────────┼──────────────────────────┐
         v                          v                          v
 ┌─────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
 │ ElastiCache     │      │ RDS Postgres 16  │      │ S3 archive bucket   │
 │ Redis 7.1       │      │ candles, alerts  │      │ Parquet objects     │
 └────────▲────────┘      └────────▲─────────┘      └────────▲────────────┘
          │                        │                         │
          │              ┌─────────┴─────────┐               │
          │              │ ECS Fargate       │               │
          └──────────────│ ingest, worker    │───────────────┘
                         │ archiver          │
                         └───────────────────┘

 Logs: CloudWatch log group /ecs/quantstream
 Image: one ECR image, retagged with the git SHA on each push
```

The template builds a VPC with two public subnets, security groups so only tasks reach Postgres and Redis, an internet-facing load balancer in front of the api, and rolling updates (`maximumPercent` 200, `minimumHealthyPercent` 100) with a deployment circuit breaker. Task commands are the same four module entry points as the laptop. `DATABASE_URL`, `REDIS_URL`, `FEED_URL`, and `ARCHIVE_BUCKET` are set on the tasks. The RDS password is letters and numbers only, because it is placed into `DATABASE_URL`.

GitHub Actions (`.github/workflows/deploy.yml`) runs on every push to `main`. The test job installs the package and runs `pytest`. The deploy job needs that to pass, then pushes the image to ECR and runs `aws cloudformation deploy` on `deploy/stack.yml`. It reads these repository secrets:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `DB_PASSWORD`
- `FEED_URL`

Empty the archive bucket before deleting the stack. CloudFormation will not delete a bucket that still has objects.

---

# Technologies

### Pipeline
- **FastAPI**: HTTP API for candles, alerts, and the chart page
- **uvicorn**: process server
- **websockets**: trade feed client
- **Redis**: stream of ticks and the worker consumer group
- **PostgreSQL + asyncpg + SQLAlchemy**: candles and alerts
- **Pydantic**: settings from the environment and API response models
- **PyArrow**: Parquet archives

### Chart
- **Same Pipeline**: synthetic prints, no database
- **Canvas page**: candlesticks, volume, and alerts in the browser

### Cloud and local runtime
- **Docker**: one image, four commands
- **Docker Compose**: Postgres 16, Redis 7, and the four processes
- **ECS Fargate**: one service each for ingest, worker, api, and archiver
- **RDS**: Postgres 16.4
- **ElastiCache**: Redis 7.1
- **S3**: archived Parquet
- **CloudWatch**: logs for each task
- **ECR**: the image built in GitHub Actions
- **CloudFormation**: the stack in `deploy/stack.yml`
- **GitHub Actions**: pytest, then image push and stack update

---

# What the project does

1. Accepts a trade stream and ignores everything except the symbols you list
2. Turns those prints into OHLC candles on a fixed interval
3. Flags a symbol when the realized volatility of recent closes crosses a threshold
4. Stores candles and alerts in Postgres and serves them from a short cache
5. Keeps an offline Parquet copy of closed candles, and can put that copy in S3
6. Runs as four processes on a laptop, or as four Fargate services behind a load balancer
7. Includes a candlestick page so the candle path can be looked at on its own
