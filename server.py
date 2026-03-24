#!/usr/bin/env python3
"""Flask server — GEX chart gallery with calendar view."""

import os
import re
import time
import calendar as cal
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from flask import Flask, send_file, render_template_string, abort, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

IMAGE_DIR = Path(__file__).resolve().parent / "gex_images"
START_TIME = time.time()
SYMBOLS = ["SPY", "QQQ", "IWM"]

HIST_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})_([A-Z]+)\.png$")


def scan_history():
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    history = defaultdict(lambda: defaultdict(list))
    for f in sorted(IMAGE_DIR.iterdir()):
        m = HIST_RE.match(f.name)
        if m:
            date_str, time_str, symbol = m.groups()
            history[date_str][symbol].append(f.name)
    return dict(history)


CALENDAR_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>GEX Calendar</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:16px;min-height:100vh}
h1{text-align:center;font-size:22px;margin-bottom:8px;color:#fff}
.subtitle{text-align:center;color:#8b949e;font-size:13px;margin-bottom:20px}
nav{display:flex;justify-content:center;gap:12px;margin-bottom:24px}
nav a{color:#58a6ff;text-decoration:none;font-size:14px;padding:6px 14px;border:1px solid #30363d;border-radius:6px;transition:all .15s}
nav a:hover,nav a.active{background:#1f6feb;color:#fff;border-color:#1f6feb}
.badge{display:inline-block;background:#238636;color:#fff;font-size:10px;padding:2px 8px;border-radius:10px;margin-left:8px}
.cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:6px;max-width:700px;margin:0 auto 24px}
.day-header{text-align:center;font-size:11px;color:#8b949e;padding:4px;font-weight:600}
.day{background:#161b22;border:1px solid #21262d;border-radius:8px;min-height:60px;padding:6px;position:relative;transition:all .15s}
.day:hover{border-color:#58a6ff}
.day.empty{background:transparent;border-color:transparent;min-height:0}
.day.today{border-color:#f0883e}
.day-num{font-size:12px;color:#8b949e;margin-bottom:4px}
.day.has-data .day-num{color:#fff;font-weight:600}
.day a{text-decoration:none;display:block;height:100%;color:inherit}
.sym-dots{display:flex;gap:3px;flex-wrap:wrap}
.dot{width:8px;height:8px;border-radius:2px}
.dot-SPY{background:#2962ff}.dot-QQQ{background:#00bcd4}.dot-IWM{background:#ff9800}
.legend{display:flex;justify-content:center;gap:16px;margin-bottom:20px;font-size:12px;color:#8b949e}
.legend-item{display:flex;align-items:center;gap:4px}
.month-nav{display:flex;justify-content:center;align-items:center;gap:16px;margin-bottom:16px}
.month-nav a{color:#58a6ff;text-decoration:none;font-size:18px;padding:4px 12px;border:1px solid #30363d;border-radius:6px}
.month-nav a:hover{background:#1f6feb;color:#fff}
.month-title{font-size:18px;font-weight:600;min-width:160px;text-align:center}
</style>
</head>
<body>
<h1>GEX Charts <span class="badge">LIVE</span></h1>
<nav><a href="/" class="active">Calendar</a><a href="/latest">Latest</a></nav>
<div class="legend">
  <div class="legend-item"><span class="dot dot-SPY"></span> SPY</div>
  <div class="legend-item"><span class="dot dot-QQQ"></span> QQQ</div>
  <div class="legend-item"><span class="dot dot-IWM"></span> IWM</div>
</div>
<div class="month-nav">
  <a href="/?month={{ prev_month }}">&larr;</a>
  <span class="month-title">{{ month_name }} {{ year }}</span>
  <a href="/?month={{ next_month }}">&rarr;</a>
</div>
<div class="cal-grid">
  <div class="day-header">Mon</div><div class="day-header">Tue</div><div class="day-header">Wed</div>
  <div class="day-header">Thu</div><div class="day-header">Fri</div><div class="day-header">Sat</div><div class="day-header">Sun</div>
  {% for cell in cells %}
    {% if cell.empty %}
      <div class="day empty"></div>
    {% else %}
      <div class="day {{ 'has-data' if cell.symbols else '' }} {{ 'today' if cell.today else '' }}">
        {% if cell.symbols %}
          <a href="/date/{{ cell.date }}">
            <div class="day-num">{{ cell.day }}</div>
            <div class="sym-dots">{% for s in cell.symbols %}<span class="dot dot-{{ s }}"></span>{% endfor %}</div>
          </a>
        {% else %}
          <div class="day-num">{{ cell.day }}</div>
        {% endif %}
      </div>
    {% endif %}
  {% endfor %}
</div>
<div class="subtitle">Click a date to see GEX charts</div>
</body></html>
"""

DATE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>GEX — {{ date }}</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:16px}
h1{text-align:center;font-size:20px;margin-bottom:6px;color:#fff}
.subtitle{text-align:center;color:#8b949e;font-size:13px;margin-bottom:20px}
nav{display:flex;justify-content:center;gap:12px;margin-bottom:24px}
nav a{color:#58a6ff;text-decoration:none;font-size:14px;padding:6px 14px;border:1px solid #30363d;border-radius:6px}
nav a:hover{background:#1f6feb;color:#fff;border-color:#1f6feb}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}
.card{background:#161b22;border:1px solid #30363d;border-radius:12px;overflow:hidden}
.card-header{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid #21262d}
.sym{font-size:18px;font-weight:700}
.spy{color:#2962ff}.qqq{color:#00bcd4}.iwm{color:#ff9800}
.ts{font-size:11px;color:#8b949e}
.img-wrap{padding:10px}
.img-wrap img{width:100%;border-radius:6px;display:block;cursor:pointer}
.no-data{padding:30px;text-align:center;color:#8b949e}
</style>
</head>
<body>
<h1>{{ date_display }}</h1>
<p class="subtitle">{{ chart_count }} chart(s)</p>
<nav><a href="/">&larr; Calendar</a><a href="/latest">Latest</a></nav>
<div class="grid">
{% for item in charts %}
  <div class="card">
    <div class="card-header">
      <span class="sym {{ item.symbol|lower }}">{{ item.symbol }}</span>
      <span class="ts">{{ item.time }}</span>
    </div>
    <div class="img-wrap">
      <a href="/file/{{ item.filename }}" target="_blank">
        <img src="/file/{{ item.filename }}" alt="{{ item.symbol }} GEX" loading="lazy">
      </a>
    </div>
  </div>
{% endfor %}
{% if not charts %}
  <div class="no-data">No charts captured on this date</div>
{% endif %}
</div>
</body></html>
"""

LATEST_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>GEX Latest</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:16px}
h1{text-align:center;font-size:20px;margin-bottom:8px;color:#fff}
nav{display:flex;justify-content:center;gap:12px;margin-bottom:24px}
nav a{color:#58a6ff;text-decoration:none;font-size:14px;padding:6px 14px;border:1px solid #30363d;border-radius:6px}
nav a:hover,nav a.active{background:#1f6feb;color:#fff;border-color:#1f6feb}
.badge{display:inline-block;background:#238636;color:#fff;font-size:10px;padding:2px 8px;border-radius:10px;margin-left:8px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}
.card{background:#161b22;border:1px solid #30363d;border-radius:12px;overflow:hidden}
.card-header{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid #21262d}
.sym{font-size:20px;font-weight:700}
.spy{color:#2962ff}.qqq{color:#00bcd4}.iwm{color:#ff9800}
.ts{font-size:11px;color:#8b949e}
.img-wrap{padding:12px}
.img-wrap img{width:100%;border-radius:6px;display:block;cursor:pointer}
.no-data{padding:40px 16px;text-align:center;color:#8b949e;font-size:14px}
footer{text-align:center;margin-top:24px;color:#8b949e;font-size:12px}
</style>
<script>
setTimeout(()=>{
  setInterval(()=>{
    document.querySelectorAll('.img-wrap img').forEach(img=>{
      img.src=img.src.split('?')[0]+'?t='+Date.now();
    });
  },5000);
},1000);
</script>
</head>
<body>
<h1>GEX Latest <span class="badge">LIVE</span></h1>
<nav><a href="/">Calendar</a><a href="/latest" class="active">Latest</a></nav>
<div class="grid">
{% for sym in symbols %}
  <div class="card">
    <div class="card-header">
      <span class="sym {{ sym|lower }}">{{ sym }}</span>
      <span class="ts">{{ timestamps.get(sym, 'No data yet') }}</span>
    </div>
    {% if sym in available %}
      <div class="img-wrap"><a href="/image/{{ sym }}" target="_blank">
        <img src="/image/{{ sym }}?t={{ cache_bust }}" alt="{{ sym }}" loading="lazy">
      </a></div>
    {% else %}
      <div class="no-data">Waiting for Tradytics capture</div>
    {% endif %}
  </div>
{% endfor %}
</div>
<footer>Images refresh every 5s &bull; Tap to open full size</footer>
</body></html>
"""


def get_image_info(symbol):
    path = IMAGE_DIR / f"latest_{symbol}.png"
    if path.exists():
        mtime = path.stat().st_mtime
        return True, time.strftime("%b %d, %H:%M", time.localtime(mtime))
    return False, None


@app.route("/")
def calendar_view():
    history = scan_history()
    m = request.args.get("month")
    month_param = None
    if m:
        try:
            month_param = datetime.strptime(m, "%Y-%m")
        except:
            pass

    now = datetime.now()
    year = month_param.year if month_param else now.year
    month = month_param.month if month_param else now.month

    month_name = cal.month_name[month]
    first_weekday, num_days = cal.monthrange(year, month)

    prev_m = datetime(year, month, 1) - timedelta(days=1)
    next_m = datetime(year, month, num_days) + timedelta(days=1)

    cells = [{"empty": True} for _ in range(first_weekday)]
    for day in range(1, num_days + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        syms = list(history.get(date_str, {}).keys())
        cells.append({
            "empty": False, "day": day, "date": date_str,
            "symbols": syms,
            "today": (year == now.year and month == now.month and day == now.day),
        })

    return render_template_string(CALENDAR_HTML,
        cells=cells, month_name=month_name, year=year,
        prev_month=prev_m.strftime("%Y-%m"), next_month=next_m.strftime("%Y-%m"))


@app.route("/date/<date_str>")
def date_detail(date_str):
    history = scan_history()
    day_data = history.get(date_str, {})
    charts = []
    for sym in SYMBOLS:
        for fname in day_data.get(sym, []):
            m = HIST_RE.match(fname)
            if m:
                charts.append({"symbol": sym, "filename": fname, "time": m.group(2).replace("-", ":")})

    try:
        date_display = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A, %B %d, %Y")
    except:
        date_display = date_str

    return render_template_string(DATE_HTML,
        date=date_str, date_display=date_display, charts=charts, chart_count=len(charts))


@app.route("/latest")
def latest():
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    available, timestamps = [], {}
    for sym in SYMBOLS:
        exists, ts = get_image_info(sym)
        if exists:
            available.append(sym)
            timestamps[sym] = ts
    return render_template_string(LATEST_HTML,
        symbols=SYMBOLS, available=available, timestamps=timestamps, cache_bust=int(time.time()))


@app.route("/image/<symbol>")
def serve_latest(symbol):
    symbol = symbol.upper()
    path = IMAGE_DIR / f"latest_{symbol}.png"
    if symbol not in SYMBOLS or not path.exists():
        abort(404)
    return send_file(path, mimetype="image/png")


@app.route("/file/<filename>")
def serve_file(filename):
    path = IMAGE_DIR / filename
    if not path.exists() or not HIST_RE.match(filename):
        abort(404)
    return send_file(path, mimetype="image/png")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "uptime_seconds": round(time.time() - START_TIME, 1)})


if __name__ == "__main__":
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    port = int(os.environ.get("PORT", 5000))
    print(f"GEX Server on port {port}")
    app.run(host="0.0.0.0", port=port)
