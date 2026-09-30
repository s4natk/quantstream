import asyncio
import random
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from quantstream.candles import bucket_start
from quantstream.models import Tick
from quantstream.pipeline import Pipeline

SYMBOLS = ("AAPL", "MSFT")
INTERVAL_SECONDS = 15


class DemoBook:
    def __init__(self) -> None:
        self.pipeline = Pipeline(INTERVAL_SECONDS, 5, 0.02)
        self._prints = 8
        self.candles = []
        self.alerts = []
        self.prices = {"AAPL": 190.0, "MSFT": 420.0}
        self.anchors = dict(self.prices)
        self._rng = random.Random()

    def seed(self, minutes: int = 20) -> None:
        rng = random.Random(7)
        opened = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        start = bucket_start(opened, INTERVAL_SECONDS)
        steps = minutes * 60 // INTERVAL_SECONDS
        saved = self._rng
        self._rng = rng
        for step in range(steps):
            tick_at = start + timedelta(seconds=INTERVAL_SECONDS * step)
            self._on_clock(
                tick_at,
                tick_at + timedelta(seconds=INTERVAL_SECONDS),
                shock=step == steps // 2,
                prints=self._prints,
            )
        self._rng = saved

    def _on_clock(
        self,
        tick_at: datetime,
        now: datetime,
        shock: bool = False,
        prints: int = 1,
    ) -> None:
        for symbol in SYMBOLS:
            price = self.prices[symbol]
            for i in range(prints):
                if prints > 1:
                    drift = self._rng.uniform(-0.85, 0.85)
                else:
                    drift = self._rng.uniform(-0.12, 0.12)
                drift += (self.anchors[symbol] - price) * 0.15
                if shock and symbol == "AAPL" and i == prints - 1:
                    drift += price * 0.04
                price = max(1.0, price + drift)
                self.prices[symbol] = price
                span = INTERVAL_SECONDS - 1
                offset = 0 if prints == 1 else int(i * span / (prints - 1))
                when = tick_at + timedelta(seconds=offset)
                size = round(self._rng.uniform(8, 40), 2)
                close_at = now if i == prints - 1 else when
                outcome = self.pipeline.on_tick(Tick(symbol, round(price, 2), size, when), close_at)
                self.candles.extend(outcome.closed)
                self.alerts.extend(outcome.alerts)
        self.candles = self.candles[-160:]
        self.alerts = self.alerts[-20:]

    def snapshot(self) -> dict:
        def candle_row(candle):
            return {
                "symbol": candle.symbol,
                "bucket": candle.bucket.isoformat(),
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
                "trade_count": candle.trade_count,
            }

        def alert_row(alert):
            return {
                "symbol": alert.symbol,
                "bucket": alert.bucket.isoformat(),
                "volatility": round(alert.volatility, 4),
                "threshold": alert.threshold,
            }

        forming = [candle_row(candle) for candle in self.pipeline.builder.open_candles()]
        closed = [candle_row(candle) for candle in self.candles]
        series = {}
        for symbol in SYMBOLS:
            history = [row for row in closed if row["symbol"] == symbol]
            live = [row for row in forming if row["symbol"] == symbol]
            series[symbol] = (history + live)[-60:]
        return {
            "ticks": self.pipeline.counters.ticks,
            "forming": forming,
            "candles": list(reversed(closed[-12:])),
            "alerts": [alert_row(alert) for alert in reversed(self.alerts[-8:])],
            "series": series,
        }

    async def run(self) -> None:
        while True:
            now = datetime.now(timezone.utc)
            self._on_clock(now, now)
            await asyncio.sleep(0.5)


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QuantStream</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; background: #0c0f14; color: #e7ecf3; }
  body { font-family: "Segoe UI", sans-serif; display: grid; grid-template-rows: 4.5rem 1fr; }
  header {
    display: flex; align-items: center; gap: 1.5rem; padding: 0 1.25rem;
    border-bottom: 1px solid #222833;
  }
  .brand { font-weight: 600; letter-spacing: 0.04em; }
  .brand span { color: #8b97a8; font-weight: 400; margin-left: 0.4rem; }
  nav { display: flex; gap: 0.4rem; }
  button {
    background: transparent; color: #8b97a8; border: 1px solid #2a3140;
    border-radius: 999px; padding: 0.35rem 0.8rem; cursor: pointer;
  }
  button.on { color: #e7ecf3; border-color: #6d7dff; }
  .quote { margin-left: auto; text-align: right; }
  .quote strong { font-size: 1.6rem; font-variant-numeric: tabular-nums; }
  .up { color: #3dd68c; }
  .down { color: #ff5d73; }
  .meta { color: #8b97a8; font-size: 0.8rem; }
  main { display: grid; grid-template-columns: 1fr 18rem; min-height: 0; }
  .chart-wrap { position: relative; min-height: 0; }
  canvas { width: 100%; height: 100%; display: block; }
  aside { border-left: 1px solid #222833; padding: 1rem; overflow: auto; }
  aside h2 {
    margin: 0 0 0.8rem; font-size: 0.75rem; letter-spacing: 0.08em;
    text-transform: uppercase; color: #8b97a8; font-weight: 600;
  }
  .alert { padding: 0.7rem 0; border-bottom: 1px solid #222833; }
  .alert b { display: block; }
  .hover {
    position: absolute; top: 0.8rem; left: 0.8rem; background: #161b24;
    border: 1px solid #2a3140; padding: 0.45rem 0.6rem; font-size: 0.75rem;
    font-variant-numeric: tabular-nums; pointer-events: none; display: none;
  }
</style>
</head>
<body>
  <header>
    <div class="brand">QuantStream <span>15s</span></div>
    <nav id="symbols"></nav>
    <div class="quote">
      <strong id="last">—</strong>
      <div class="meta" id="change"></div>
    </div>
  </header>
  <main>
    <div class="chart-wrap">
      <canvas id="chart"></canvas>
      <div class="hover" id="hover"></div>
    </div>
    <aside>
      <h2>Volatility alerts</h2>
      <div id="alerts"></div>
    </aside>
  </main>
<script>
let symbol = "AAPL";
let latest = null;
const canvas = document.getElementById("chart");
const hover = document.getElementById("hover");
const ctx = canvas.getContext("2d");

function money(n) { return Number(n).toFixed(2); }

function resize() {
  const rect = canvas.parentElement.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * ratio));
  canvas.height = Math.max(1, Math.floor(rect.height * ratio));
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
}

function draw(bars) {
  const width = canvas.parentElement.clientWidth;
  const height = canvas.parentElement.clientHeight;
  ctx.clearRect(0, 0, width, height);
  if (!bars.length) return;
  const pad = { top: 24, right: 64, bottom: 28, left: 12 };
  const plotH = height - pad.top - pad.bottom;
  const priceH = plotH * 0.78;
  const volTop = pad.top + priceH + 10;
  const volH = height - volTop - pad.bottom;
  let lo = Math.min(...bars.map((b) => b.low));
  let hi = Math.max(...bars.map((b) => b.high));
  const span = hi - lo || 1;
  lo -= span * 0.08;
  hi += span * 0.08;
  const maxVol = Math.max(...bars.map((b) => b.volume)) || 1;
  const slot = (width - pad.left - pad.right) / bars.length;
  const bodyW = Math.max(3, slot * 0.62);
  const yPrice = (p) => pad.top + ((hi - p) / (hi - lo)) * priceH;

  ctx.strokeStyle = "#222833";
  ctx.lineWidth = 1;
  ctx.font = "11px Segoe UI, sans-serif";
  ctx.fillStyle = "#8b97a8";
  for (let i = 0; i < 4; i++) {
    const p = lo + ((hi - lo) * i) / 3;
    const y = yPrice(p);
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(width - pad.right, y);
    ctx.stroke();
    ctx.fillText(money(p), width - pad.right + 8, y + 4);
  }

  bars.forEach((bar, i) => {
    const x = pad.left + slot * i + slot / 2;
    const up = bar.close >= bar.open;
    const color = up ? "#3dd68c" : "#ff5d73";
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(x, yPrice(bar.high));
    ctx.lineTo(x, yPrice(bar.low));
    ctx.stroke();
    const top = yPrice(Math.max(bar.open, bar.close));
    const bot = yPrice(Math.min(bar.open, bar.close));
    ctx.fillRect(x - bodyW / 2, top, bodyW, Math.max(1, bot - top));
    ctx.globalAlpha = 0.35;
    const volPx = (bar.volume / maxVol) * volH;
    ctx.fillRect(x - bodyW / 2, volTop + volH - volPx, bodyW, volPx);
    ctx.globalAlpha = 1;
  });
}

function paint(data) {
  latest = data;
  const bars = data.series[symbol] || [];
  const last = bars[bars.length - 1];
  const first = bars[0];
  const lastEl = document.getElementById("last");
  const changeEl = document.getElementById("change");
  if (last && first) {
    const delta = last.close - first.open;
    const pct = (delta / first.open) * 100;
    lastEl.textContent = money(last.close);
    lastEl.className = delta >= 0 ? "up" : "down";
    const sign = delta >= 0 ? "+" : "";
    changeEl.textContent =
      sign + money(delta) + "  " + sign + pct.toFixed(2) + "%   " + data.ticks + " trades";
  }
  const names = Object.keys(data.series);
  const nav = document.getElementById("symbols");
  if (nav.dataset.names !== names.join()) {
    nav.dataset.names = names.join();
    nav.innerHTML = names.map((name) =>
      '<button data-symbol="' + name + '">' + name + "</button>"
    ).join("");
    nav.querySelectorAll("button").forEach((button) => {
      button.onclick = () => { symbol = button.dataset.symbol; paint(latest); };
    });
  }
  nav.querySelectorAll("button").forEach((button) => {
    button.className = button.dataset.symbol === symbol ? "on" : "";
  });
  const mine = data.alerts.filter((alert) => alert.symbol === symbol);
  document.getElementById("alerts").innerHTML = mine.length ? mine.map((alert) =>
    '<div class="alert"><b class="down">' + alert.symbol + " " + alert.volatility + "</b>" +
    '<div class="meta">threshold ' + alert.threshold + " " +
    alert.bucket.slice(11, 19) + "</div></div>"
  ).join("") : '<div class="meta">No alert on this name.</div>';
  resize();
  draw(bars);
}

canvas.addEventListener("mousemove", (event) => {
  if (!latest) return;
  const bars = latest.series[symbol] || [];
  const rect = canvas.getBoundingClientRect();
  const slot = (rect.width - 76) / Math.max(bars.length, 1);
  const index = Math.floor((event.clientX - rect.left - 12) / slot);
  const bar = bars[index];
  if (!bar) { hover.style.display = "none"; return; }
  hover.style.display = "block";
  hover.innerHTML = bar.bucket.slice(11, 19) +
    "<br>O " + money(bar.open) + " H " + money(bar.high) +
    "<br>L " + money(bar.low) + " C " + money(bar.close);
});
canvas.addEventListener("mouseleave", () => { hover.style.display = "none"; });
window.addEventListener("resize", () => { if (latest) paint(latest); });

async function tick() {
  const response = await fetch("/demo/state");
  paint(await response.json());
}
tick();
setInterval(tick, 1000);
</script>
</body>
</html>
"""


def create_demo_app(book: DemoBook | None = None) -> FastAPI:
    demo = book or DemoBook()
    demo.seed()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = asyncio.create_task(demo.run())
        yield
        task.cancel()

    app = FastAPI(title="QuantStream", lifespan=lifespan)

    @app.get("/", response_class=HTMLResponse)
    async def page() -> str:
        return PAGE

    @app.get("/demo/state")
    async def state() -> dict:
        return demo.snapshot()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def main() -> None:
    import uvicorn

    uvicorn.run(create_demo_app(), host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
