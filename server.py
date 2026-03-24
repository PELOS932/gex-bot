#!/usr/bin/env python3
"""Simple Flask server — serves latest GEX chart images."""

import os
import time
from pathlib import Path
from flask import Flask, send_file, render_template_string, abort, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

IMAGE_DIR  = Path(__file__).resolve().parent / "gex_images"
START_TIME = time.time()
SYMBOLS    = ["SPY", "QQQ", "IWM"]

GALLERY_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="60">
<title>GEX Charts</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#0d1117; color:#e6edf3; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; padding:16px; }
  h1  { text-align:center; font-size:20px; margin-bottom:20px; color:#fff; letter-spacing:1px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:16px; }
  .card { background:#161b22; border:1px solid #30363d; border-radius:12px; overflow:hidden; }
  .card-header { display:flex; justify-content:space-between; align-items:center; padding:12px 16px; border-bottom:1px solid #21262d; }
  .sym { font-size:20px; font-weight:700; }
  .spy { color:#2962ff; } .qqq { color:#00bcd4; } .iwm { color:#ff9800; }
  .ts  { font-size:11px; color:#8b949e; }
  .img-wrap { padding:12px; }
  .img-wrap img { width:100%; border-radius:6px; display:block; cursor:pointer; }
  .no-data { padding:40px 16px; text-align:center; color:#8b949e; font-size:14px; }
  .badge { display:inline-block; background:#238636; color:#fff; font-size:10px; padding:2px 8px; border-radius:10px; margin-left:8px; }
  footer { text-align:center; margin-top:24px; color:#8b949e; font-size:12px; }
  @media(max-width:500px){ body{padding:8px;} .card-header{padding:10px 12px;} }
</style>
</head>
<body>
<h1>GEX Charts <span class="badge">LIVE</span></h1>
<div class="grid">
{% for sym in symbols %}
  <div class="card">
    <div class="card-header">
      <span class="sym {{ sym.lower() }}">{{ sym }}</span>
      <span class="ts">{{ timestamps.get(sym, 'No data yet') }}</span>
    </div>
    {% if sym in available %}
      <div class="img-wrap">
        <a href="/image/{{ sym }}" target="_blank">
          <img src="/image/{{ sym }}?t={{ cache_bust }}" alt="{{ sym }} GEX Chart" loading="lazy">
        </a>
      </div>
    {% else %}
      <div class="no-data">No chart yet — waiting for Tradytics capture</div>
    {% endif %}
  </div>
{% endfor %}
</div>
<footer>Auto-refreshes every 60s &bull; Tap image to open full size</footer>
</body>
</html>
"""


def get_image_info(symbol: str):
    path = IMAGE_DIR / f"latest_{symbol}.png"
    if path.exists():
        mtime = path.stat().st_mtime
        ts = time.strftime("%b %d, %H:%M", time.localtime(mtime))
        return True, ts
    return False, None


@app.route("/")
@app.route("/charts")
def gallery():
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    available   = []
    timestamps  = {}
    for sym in SYMBOLS:
        exists, ts = get_image_info(sym)
        if exists:
            available.append(sym)
            timestamps[sym] = ts
    return render_template_string(
        GALLERY_HTML,
        symbols=SYMBOLS,
        available=available,
        timestamps=timestamps,
        cache_bust=int(time.time()),
    )


@app.route("/image/<symbol>")
def serve_image(symbol: str):
    symbol = symbol.upper()
    if symbol not in SYMBOLS:
        abort(404)
    path = IMAGE_DIR / f"latest_{symbol}.png"
    if not path.exists():
        abort(404)
    return send_file(path, mimetype="image/png")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "uptime_seconds": round(time.time() - START_TIME, 1)})


if __name__ == "__main__":
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    port = int(os.environ.get("PORT", 5000))
    print(f"GEX Image Server running on port {port}")
    app.run(host="0.0.0.0", port=port)
