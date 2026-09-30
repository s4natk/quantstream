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
                outcome = self.pipeline.on_tick(
                    Tick(symbol, round(price, 2), size, when),
                    close_at,
                )
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
            series[symbol] = (history + live)[-150:]
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


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QuantStream</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; background: #0b1016; color: #e6edf5; }
  body {
    font-family: "Segoe UI", sans-serif;
    display: grid; grid-template-rows: auto 1fr;
  }
  header {
    display: flex; align-items: center; gap: 0.8rem; flex-wrap: wrap;
    padding: 0.65rem 1rem; border-bottom: 1px solid #1c2633; background: #10161d;
  }
  .brand { font-weight: 650; letter-spacing: 0.06em; }
  .brand span { color: #7d8b9c; font-weight: 500; margin-left: 0.45rem; }
  .dot {
    width: 0.45rem; height: 0.45rem; border-radius: 50%; background: #3ecf8e;
    display: inline-block; margin-right: 0.4rem; box-shadow: 0 0 0 3px #163528;
  }
  nav, .modes { display: flex; gap: 0.35rem; align-items: center; }
  button {
    background: transparent; color: #7d8b9c; border: 1px solid #2a3544;
    border-radius: 999px; padding: 0.32rem 0.7rem; cursor: pointer;
    font: inherit;
  }
  button.on { color: #e6edf5; border-color: #e0a45a; background: #2a2116; }
  .modes {
    border: 1px solid #2a3544; border-radius: 8px; overflow: hidden; gap: 0;
  }
  .modes button { border: 0; border-radius: 0; border-right: 1px solid #2a3544; }
  .modes button:last-child { border-right: 0; }
  .quote { margin-left: auto; text-align: right; }
  .quote strong { font-size: 1.45rem; font-variant-numeric: tabular-nums; }
  .up { color: #3ecf8e; }
  .down { color: #f07178; }
  .meta { color: #7d8b9c; font-size: 0.78rem; }
  main { display: grid; grid-template-columns: 1fr 19rem; min-height: 0; }
  .chart-wrap { position: relative; min-height: 0; background: #070b10; cursor: crosshair; }
  .chart-wrap.zone-y { cursor: ns-resize; }
  .chart-wrap.zone-x { cursor: ew-resize; }
  canvas { width: 100%; height: 100%; display: block; }
  .hint {
    position: absolute; left: 0.75rem; top: 0.55rem; color: #667586;
    font-size: 0.72rem; pointer-events: none;
  }
  aside {
    border-left: 1px solid #1c2633; background: #10161d;
    padding: 0.9rem 1rem; overflow: auto;
  }
  aside h2 {
    margin: 0.2rem 0 0.55rem; font-size: 0.72rem; letter-spacing: 0.08em;
    text-transform: uppercase; color: #7d8b9c; font-weight: 650;
  }
  .row {
    display: flex; justify-content: space-between; gap: 1rem;
    padding: 0.28rem 0; border-bottom: 1px solid #1c2633;
    font-variant-numeric: tabular-nums; font-size: 0.86rem;
  }
  .row span { color: #7d8b9c; }
  .alert { padding: 0.65rem 0; border-bottom: 1px solid #1c2633; }
  .alert b { display: block; }
  .split { height: 1rem; }
  @media (max-width: 860px) {
    main { grid-template-columns: 1fr; grid-template-rows: minmax(22rem, 1fr) auto; }
    aside { border-left: 0; border-top: 1px solid #1c2633; max-height: 16rem; }
    .quote { margin-left: 0; }
  }
</style>
</head>
<body>
  <header>
    <div class="brand"><i class="dot"></i>QuantStream <span>15s</span></div>
    <nav id="symbols"></nav>
    <div class="modes" id="modes">
      <button type="button" data-view="candles" class="on">Candles</button>
      <button type="button" data-view="bars">OHLC</button>
      <button type="button" data-view="line">Line</button>
      <button type="button" data-view="area">Area</button>
      <button type="button" data-view="heikin">Heikin</button>
    </div>
    <button type="button" id="fit">Fit</button>
    <div class="quote">
      <strong id="last">—</strong>
      <div class="meta" id="change"></div>
    </div>
  </header>
  <main>
    <div class="chart-wrap" id="wrap">
      <canvas id="chart"></canvas>
      <div class="hint">Scroll to zoom. Drag to pan. Drag the price scale or the time scale.</div>
    </div>
    <aside>
      <h2>Bar</h2>
      <div id="bar"></div>
      <div class="split"></div>
      <h2>Volatility alerts</h2>
      <div id="alerts"></div>
    </aside>
  </main>
<script>
const UP = "#3ecf8e";
const DOWN = "#f07178";
const MUTED = "#7d8b9c";
const GRID = "#1b2633";
const ACCENT = "#e0a45a";

let symbol = "AAPL";
let view = "candles";
let latest = null;
let visible = 32;
let rightPad = 0;
let follow = true;
let pricePad = 0.12;
let pinned = null;
let mark = null;
let cursor = null;
let drag = null;
let frame = null;

const canvas = document.getElementById("chart");
const wrap = document.getElementById("wrap");
const ctx = canvas.getContext("2d");

function clamp(n, lo, hi) {
  return Math.max(lo, Math.min(hi, n));
}
function money(n) {
  return Number(n).toFixed(2);
}
function tone(bar) {
  return bar.close >= bar.open ? UP : DOWN;
}
function stamp(bar) {
  return bar.bucket.slice(11, 19);
}
function rawSeries() {
  if (!latest || !latest.series) return [];
  return latest.series[symbol] || [];
}
function plotted() {
  const bars = rawSeries();
  if (view !== "heikin" || bars.length === 0) return bars;
  const out = [];
  let prevOpen = bars[0].open;
  let prevClose = bars[0].close;
  bars.forEach((bar) => {
    const close = (bar.open + bar.high + bar.low + bar.close) / 4;
    const open = (prevOpen + prevClose) / 2;
    out.push({
      symbol: bar.symbol,
      bucket: bar.bucket,
      volume: bar.volume,
      trade_count: bar.trade_count,
      open: open,
      close: close,
      high: Math.max(bar.high, open, close),
      low: Math.min(bar.low, open, close),
    });
    prevOpen = open;
    prevClose = close;
  });
  return out;
}
function windowed() {
  const all = plotted();
  const count = all.length;
  if (!count) return { bars: [], start: 0 };
  const shown = clamp(visible, 8, count);
  if (follow) rightPad = 0;
  rightPad = clamp(rightPad, 0, Math.max(0, count - shown));
  const end = count - rightPad;
  const start = end - shown;
  return { bars: all.slice(start, end), start: start };
}
function metrics(width, height, count) {
  const pad = { top: 16, right: 76, bottom: 30, left: 8 };
  const room = height - pad.top - pad.bottom;
  const priceH = room * 0.74;
  const volTop = pad.top + priceH + 8;
  const volH = Math.max(8, height - pad.bottom - volTop);
  const slot = (width - pad.left - pad.right) / Math.max(count, 1);
  return { pad, priceH, volTop, volH, slot, width, height };
}
function rangeOf(bars) {
  const closes = view === "line" || view === "area";
  let lo = Infinity;
  let hi = -Infinity;
  bars.forEach((bar) => {
    lo = Math.min(lo, closes ? bar.close : bar.low);
    hi = Math.max(hi, closes ? bar.close : bar.high);
  });
  const span = (hi - lo) || 1;
  return { lo: lo - span * pricePad, hi: hi + span * pricePad };
}
function yOf(price, range, box) {
  const t = (range.hi - price) / (range.hi - range.lo || 1);
  return box.pad.top + t * box.priceH;
}
function priceOf(y, range, box) {
  const t = (y - box.pad.top) / box.priceH;
  return range.hi - t * (range.hi - range.lo);
}
function resize() {
  const rect = wrap.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * ratio));
  canvas.height = Math.max(1, Math.floor(rect.height * ratio));
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { width: rect.width, height: rect.height };
}
function xAt(box, i) {
  return box.pad.left + box.slot * i + box.slot / 2;
}
function drawGrid(box, range) {
  ctx.font = "11px Segoe UI, sans-serif";
  ctx.fillStyle = "#070b10";
  ctx.fillRect(0, 0, box.width, box.height);
  ctx.fillStyle = "#0d141c";
  ctx.fillRect(box.width - box.pad.right, 0, box.pad.right, box.height);
  ctx.fillRect(0, box.height - box.pad.bottom, box.width, box.pad.bottom);
  ctx.strokeStyle = GRID;
  ctx.lineWidth = 1;
  ctx.fillStyle = MUTED;
  for (let i = 0; i < 5; i++) {
    const price = range.lo + ((range.hi - range.lo) * i) / 4;
    const y = yOf(price, range, box);
    ctx.beginPath();
    ctx.moveTo(box.pad.left, y);
    ctx.lineTo(box.width - box.pad.right, y);
    ctx.stroke();
    ctx.fillText(money(price), box.width - box.pad.right + 8, y + 4);
  }
}
function drawCandles(bars, box, range) {
  const bodyW = Math.max(2, box.slot * 0.62);
  bars.forEach((bar, i) => {
    const x = xAt(box, i);
    const color = tone(bar);
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(x, yOf(bar.high, range, box));
    ctx.lineTo(x, yOf(bar.low, range, box));
    ctx.stroke();
    const top = yOf(Math.max(bar.open, bar.close), range, box);
    const bot = yOf(Math.min(bar.open, bar.close), range, box);
    ctx.fillRect(x - bodyW / 2, top, bodyW, Math.max(1, bot - top));
  });
}
function drawBars(bars, box, range) {
  const arm = Math.max(3, box.slot * 0.28);
  bars.forEach((bar, i) => {
    const x = xAt(box, i);
    ctx.strokeStyle = tone(bar);
    ctx.beginPath();
    ctx.moveTo(x, yOf(bar.high, range, box));
    ctx.lineTo(x, yOf(bar.low, range, box));
    ctx.moveTo(x - arm, yOf(bar.open, range, box));
    ctx.lineTo(x, yOf(bar.open, range, box));
    ctx.moveTo(x, yOf(bar.close, range, box));
    ctx.lineTo(x + arm, yOf(bar.close, range, box));
    ctx.stroke();
  });
}
function drawLine(bars, box, range, fill) {
  if (!bars.length) return;
  const bottom = box.pad.top + box.priceH;
  ctx.beginPath();
  bars.forEach((bar, i) => {
    const x = xAt(box, i);
    const y = yOf(bar.close, range, box);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  if (fill) {
    const lastX = xAt(box, bars.length - 1);
    ctx.lineTo(lastX, bottom);
    ctx.lineTo(xAt(box, 0), bottom);
    ctx.closePath();
    ctx.fillStyle = "rgba(224,164,90,0.16)";
    ctx.fill();
    ctx.beginPath();
    bars.forEach((bar, i) => {
      const x = xAt(box, i);
      const y = yOf(bar.close, range, box);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
  }
  const up = bars[bars.length - 1].close >= bars[0].close;
  ctx.strokeStyle = fill ? ACCENT : (up ? UP : DOWN);
  ctx.lineWidth = 1.6;
  ctx.stroke();
  ctx.lineWidth = 1;
}
function drawVolume(bars, box) {
  const maxVol = Math.max(...bars.map((bar) => bar.volume)) || 1;
  const bodyW = Math.max(2, box.slot * 0.62);
  bars.forEach((bar, i) => {
    const x = xAt(box, i);
    const h = (bar.volume / maxVol) * box.volH;
    ctx.globalAlpha = 0.45;
    ctx.fillStyle = tone(bar);
    ctx.fillRect(x - bodyW / 2, box.volTop + box.volH - h, bodyW, h);
    ctx.globalAlpha = 1;
  });
}
function drawTimes(bars, box) {
  if (!bars.length) return;
  const marks = [0, Math.floor((bars.length - 1) / 2), bars.length - 1];
  ctx.fillStyle = MUTED;
  marks.forEach((i) => {
    const text = stamp(bars[i]);
    const x = xAt(box, i) - ctx.measureText(text).width / 2;
    ctx.fillText(text, x, box.height - 10);
  });
}
function drawParts(bar, i, box, range) {
  const x = xAt(box, i);
  const half = Math.max(5, box.slot * 0.46);
  ["high", "low", "open", "close"].forEach((key) => {
    const y = yOf(bar[key], range, box);
    ctx.strokeStyle = key === "open" || key === "close" ? tone(bar) : MUTED;
    ctx.beginPath();
    ctx.moveTo(x - half, y);
    ctx.lineTo(x + half, y);
    ctx.stroke();
  });
}
function drawTag(text, x, y, fill) {
  const w = ctx.measureText(text).width + 10;
  ctx.fillStyle = fill;
  ctx.fillRect(x, y, w, 16);
  ctx.fillStyle = "#140e06";
  ctx.fillText(text, x + 5, y + 12);
}
function draw() {
  const size = resize();
  const pack = windowed();
  const bars = pack.bars;
  ctx.clearRect(0, 0, size.width, size.height);
  if (!bars.length) {
    frame = null;
    return;
  }
  const box = metrics(size.width, size.height, bars.length);
  const range = rangeOf(bars);
  frame = { box, range, bars, start: pack.start, width: size.width, height: size.height };
  drawGrid(box, range);
  if (view === "line") drawLine(bars, box, range, false);
  else if (view === "area") drawLine(bars, box, range, true);
  else if (view === "bars") drawBars(bars, box, range);
  else drawCandles(bars, box, range);
  drawVolume(bars, box);
  drawTimes(bars, box);
  if (pinned) {
    const index = bars.findIndex((bar) => bar.bucket === pinned);
    if (index >= 0) {
      ctx.strokeStyle = ACCENT;
      ctx.strokeRect(
        box.pad.left + box.slot * index + 1,
        box.pad.top,
        Math.max(1, box.slot - 2),
        box.priceH,
      );
      drawParts(bars[index], index, box, range);
    }
  }
  if (mark != null) {
    const y = yOf(mark, range, box);
    ctx.strokeStyle = ACCENT;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(box.pad.left, y);
    ctx.lineTo(box.width - box.pad.right, y);
    ctx.stroke();
    ctx.setLineDash([]);
    drawTag(money(mark), box.width - box.pad.right, y - 8, ACCENT);
  }
  const last = bars[bars.length - 1];
  const yLast = yOf(last.close, range, box);
  ctx.strokeStyle = tone(last);
  ctx.setLineDash([2, 3]);
  ctx.beginPath();
  ctx.moveTo(box.pad.left, yLast);
  ctx.lineTo(box.width - box.pad.right, yLast);
  ctx.stroke();
  ctx.setLineDash([]);
  const cursorNear = cursor && cursor.zone !== "x" && Math.abs(cursor.y - yLast) < 20;
  if (!cursorNear) {
    ctx.fillStyle = tone(last);
    ctx.fillRect(box.width - box.pad.right, yLast - 8, box.pad.right, 16);
    ctx.fillStyle = "#07110d";
    ctx.fillText(money(last.close), box.width - box.pad.right + 6, yLast + 4);
  }
  if (!cursor || cursor.zone === "outside") return;
  ctx.strokeStyle = "rgba(224,164,90,0.9)";
  ctx.setLineDash([3, 3]);
  ctx.beginPath();
  if (cursor.zone !== "x") {
    ctx.moveTo(box.pad.left, cursor.y);
    ctx.lineTo(box.width - box.pad.right, cursor.y);
  }
  if (cursor.zone !== "y") {
    ctx.moveTo(cursor.x, box.pad.top);
    ctx.lineTo(cursor.x, box.height - box.pad.bottom);
  }
  ctx.stroke();
  ctx.setLineDash([]);
  if (cursor.zone !== "x") {
    drawTag(money(cursor.price), box.width - box.pad.right, cursor.y - 8, ACCENT);
  }
  if (cursor.bar && cursor.zone !== "y") {
    const text = stamp(cursor.bar);
    const w = ctx.measureText(text).width + 10;
    drawTag(text, cursor.x - w / 2, box.height - box.pad.bottom + 4, ACCENT);
  }
}
function locate(event) {
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  if (!frame) return { zone: "plot", x, y, index: -1, bar: null, price: null };
  const box = frame.box;
  let zone = "plot";
  if (x >= rect.width - box.pad.right) zone = "y";
  else if (y >= rect.height - box.pad.bottom) zone = "x";
  else if (x < box.pad.left || y < box.pad.top) zone = "plot";
  const index = Math.floor((x - box.pad.left) / box.slot);
  const bar = frame.bars[index] || null;
  return { zone, x, y, index, bar, price: priceOf(y, frame.range, box) };
}
function row(label, value, cls) {
  const toneClass = cls ? " class=\"" + cls + "\"" : "";
  return "<div class=\"row\"><span>" + label + "</span><b" + toneClass + ">" + value + "</b></div>";
}
function fillPanel() {
  const el = document.getElementById("bar");
  const found = plotted().find((item) => item.bucket === pinned);
  const bar = (cursor && cursor.bar) || (pinned && found);
  if (!bar) {
    el.innerHTML = "<p class=\"meta\">Hover a bar, or click one to pin it. " +
      "Click the price scale to mark a level. Click the time scale to pin that bar.</p>";
    return;
  }
  const cls = bar.close >= bar.open ? "up" : "down";
  let html = row("Time", stamp(bar), "");
  html += row("Open", money(bar.open), "");
  html += row("High", money(bar.high), "up");
  html += row("Low", money(bar.low), "down");
  html += row("Close", money(bar.close), cls);
  html += row("Volume", money(bar.volume), "");
  if (cursor && cursor.price != null && cursor.zone !== "x") {
    html += row("Cursor Y", money(cursor.price), "");
  }
  if (mark != null) html += row("Y mark", money(mark), "");
  if (pinned === bar.bucket) html += "<p class=\"meta\">Pinned</p>";
  if (view === "heikin") html += "<p class=\"meta\">Heikin bars average open and close.</p>";
  el.innerHTML = html;
}
function paintQuote() {
  const bars = rawSeries();
  const last = bars[bars.length - 1];
  const first = bars[0];
  const lastEl = document.getElementById("last");
  const changeEl = document.getElementById("change");
  if (!last || !first || !first.open) return;
  const delta = last.close - first.open;
  const pct = (delta / first.open) * 100;
  const sign = delta >= 0 ? "+" : "";
  lastEl.textContent = money(last.close);
  lastEl.className = delta >= 0 ? "up" : "down";
  changeEl.textContent = sign + money(delta) + "   " + sign + pct.toFixed(2) + "%   " +
    latest.ticks + " trades";
}
function paintNav() {
  const names = Object.keys((latest && latest.series) || {});
  const nav = document.getElementById("symbols");
  if (nav.dataset.names !== names.join()) {
    nav.dataset.names = names.join();
    nav.innerHTML = names.map((name) =>
      "<button type=\"button\" data-symbol=\"" + name + "\">" + name + "</button>"
    ).join("");
    nav.querySelectorAll("button").forEach((button) => {
      button.onclick = () => selectSymbol(button.dataset.symbol);
    });
  }
  nav.querySelectorAll("button").forEach((button) => {
    button.className = button.dataset.symbol === symbol ? "on" : "";
  });
}
function paintAlerts() {
  const mine = (latest.alerts || []).filter((alert) => alert.symbol === symbol);
  const html = mine.length ? mine.map((alert) =>
    "<div class=\"alert\"><b class=\"down\">" + alert.symbol + "  " + alert.volatility +
    "</b><div class=\"meta\">threshold " + alert.threshold + "  " +
    alert.bucket.slice(11, 19) + "</div></div>"
  ).join("") : "<div class=\"meta\">No alert on this name.</div>";
  document.getElementById("alerts").innerHTML = html;
}
function redraw() {
  draw();
  fillPanel();
}
function paint(data) {
  latest = data;
  paintQuote();
  paintNav();
  paintAlerts();
  redraw();
}
function selectSymbol(name) {
  symbol = name;
  pinned = null;
  mark = null;
  follow = true;
  rightPad = 0;
  if (latest) paint(latest);
}
function fit() {
  visible = 32;
  rightPad = 0;
  follow = true;
  pricePad = 0.12;
  pinned = null;
  mark = null;
  redraw();
}
document.getElementById("modes").onclick = (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  view = button.dataset.view;
  document.querySelectorAll("#modes button").forEach((el) => {
    el.className = el.dataset.view === view ? "on" : "";
  });
  redraw();
};
document.getElementById("fit").onclick = fit;
canvas.addEventListener("pointerdown", (event) => {
  const hit = locate(event);
  drag = {
    x: event.clientX,
    y: event.clientY,
    zone: hit.zone,
    rightPad: rightPad,
    pricePad: pricePad,
    visible: visible,
    slot: frame ? frame.box.slot : 8,
  };
  canvas.setPointerCapture(event.pointerId);
});
canvas.addEventListener("pointermove", (event) => {
  cursor = locate(event);
  wrap.classList.toggle("zone-y", cursor.zone === "y");
  wrap.classList.toggle("zone-x", cursor.zone === "x");
  if (drag) {
    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    if (drag.zone === "y") {
      pricePad = clamp(drag.pricePad * Math.exp(dy * 0.008), 0.02, 1.4);
    } else if (drag.zone === "x") {
      const count = Math.max(8, plotted().length);
      visible = clamp(Math.round(drag.visible + dx / 6), 8, count);
    } else {
      const moved = Math.round(dx / Math.max(drag.slot, 4));
      rightPad = Math.max(0, drag.rightPad + moved);
      follow = false;
    }
  }
  redraw();
});
canvas.addEventListener("pointerup", (event) => {
  if (!drag) return;
  const moved = Math.abs(event.clientX - drag.x) + Math.abs(event.clientY - drag.y);
  const hit = locate(event);
  drag = null;
  if (moved > 8) {
    redraw();
    return;
  }
  if (hit.zone === "y") mark = hit.price;
  else if (hit.bar) pinned = pinned === hit.bar.bucket ? null : hit.bar.bucket;
  redraw();
});
canvas.addEventListener("pointerleave", () => {
  if (drag) return;
  cursor = null;
  wrap.classList.remove("zone-y", "zone-x");
  redraw();
});
canvas.addEventListener("wheel", (event) => {
  event.preventDefault();
  const hit = locate(event);
  const count = Math.max(plotted().length, 1);
  if (hit.zone === "y") {
    pricePad = clamp(pricePad * (event.deltaY > 0 ? 1.18 : 0.84), 0.02, 1.4);
  } else {
    const old = visible;
    const next = event.deltaY > 0 ? Math.ceil(old * 1.12) : Math.floor(old / 1.12);
    visible = clamp(next, 8, count);
    if (hit.bar && frame && hit.index >= 0) {
      const abs = frame.start + hit.index;
      const frac = hit.index / Math.max(old, 1);
      const shown = Math.min(visible, count);
      const end = abs + (shown - Math.round(frac * shown));
      rightPad = clamp(count - end, 0, Math.max(0, count - 8));
      follow = rightPad === 0;
    }
  }
  redraw();
}, { passive: false });
window.addEventListener("resize", () => { if (latest) redraw(); });
canvas.addEventListener("dblclick", fit);

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
