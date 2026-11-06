"""live.html: watch a playtest run as it happens.

Each worker writes live/w<n>.png (its screen) and live/w<n>.js (what it's
doing) about once a second; a worker playing at normal speed (--watch)
writes ~15 times a second. The page reloads them in place. It works when
opened straight from the folder: no web server needed.
"""

from __future__ import annotations

from pathlib import Path

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Playtest Live</title>
<style>
:root { --bg:#fbfbfa; --fg:#1d1d1b; --muted:#6b6b66; --line:#e4e3df; --card:#fff; --accent:#c2410c; --ok:#2e7d32; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#161615; --fg:#ecebe8; --muted:#a3a29d;
  --line:#33322f; --card:#1f1f1d; --accent:#fb923c; --ok:#81c784; } }
body { background:var(--bg); color:var(--fg); font:15px/1.45 system-ui, sans-serif; margin:0; padding:20px 16px; }
main { max-width:1100px; margin:0 auto; }
h1 { font-size:22px; margin:0 0 4px; } .muted { color:var(--muted); }
a { color:inherit; }
.grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(260px, 1fr)); gap:14px; margin-top:16px; }
.panel { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:10px; }
.panel.watch { grid-column:1 / -1; max-width:760px; }
.screen { width:100%; aspect-ratio:3 / 2; image-rendering:pixelated; background:#000; border-radius:6px; display:block; }
.head { display:flex; justify-content:space-between; gap:8px; margin:8px 0 2px; font-weight:600; }
.tag { font-size:12px; font-weight:600; color:var(--accent); white-space:nowrap; }
.tag.ok { color:var(--ok); }
.info { font-size:13px; color:var(--muted); overflow-wrap:anywhere; }
.stale { opacity:.45; }
#waiting { margin-top:24px; }
</style></head><body><main>
<h1>Playtest live view</h1>
<p class="muted">Each panel is one emulator. Full-speed ones update about once a second, so expect jumps;
a "normal speed" one plays at the game's real speed. The <a href="report.html">report</a> has the results so far.</p>
<p id="waiting" class="muted">Waiting for the first game to start (making the new-game saves takes a few minutes)...</p>
<div class="grid" id="grid"></div>
</main>
<script>
var WORKERS = __WORKERS__;
var grid = document.getElementById("grid");
var panels = {};

function panel(w) {
  if (panels[w]) return panels[w];
  var div = document.createElement("div");
  div.className = "panel";
  div.innerHTML = '<img class="screen" alt="emulator ' + (w + 1) + ' screen">' +
    '<div class="head"><span class="title">Emulator ' + (w + 1) + '</span><span class="tag"></span></div>' +
    '<div class="info"></div>';
  grid.appendChild(div);
  panels[w] = { div: div, img: div.querySelector("img"), tag: div.querySelector(".tag"),
                info: div.querySelector(".info"), loading: false, last: 0 };
  return panels[w];
}

function refreshImage(p, w) {
  if (p.loading) return;
  p.loading = true;
  var next = new Image();  // load off-screen, then swap: no flicker
  next.onload = function () { p.img.src = next.src; p.loading = false; };
  next.onerror = function () { p.loading = false; };
  next.src = "live/w" + w + ".png?t=" + Date.now();
}

function loadStatus(w) {
  var old = document.getElementById("status" + w);
  if (old) old.remove();
  var s = document.createElement("script");
  s.id = "status" + w;
  s.src = "live/w" + w + ".js?t=" + Date.now();
  document.body.appendChild(s);
}

function esc(t) { return String(t).replace(/[&<>]/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;"}[c]; }); }

function render() {
  var st = window.liveStatus || {};
  var any = false;
  for (var w = 0; w < WORKERS; w++) {
    var info = st[w];
    if (!info) continue;
    any = true;
    var p = panel(w);
    p.div.classList.toggle("watch", !!info.normal_speed);
    if (info.normal_speed && grid.firstChild !== p.div) grid.insertBefore(p.div, grid.firstChild);
    p.tag.textContent = info.normal_speed ? "normal speed" : (info.in_battle ? "in battle" : "full speed");
    p.tag.classList.toggle("ok", !!info.normal_speed);
    var age = Date.now() / 1000 - info.updated;
    p.div.classList.toggle("stale", age > 30);
    p.info.innerHTML = "<b>" + esc(info.map.replace(/_/g, " ")) + "</b>" +
      (info.party.length ? "<br>" + esc(info.party.join(", ")) : "") +
      "<br>" + info.badges + " badge" + (info.badges === 1 ? "" : "s") +
      " &middot; started from " + esc(info.start) +
      "<br>" + info.total.toLocaleString() + " presses &middot; " + info.problems +
      " problem" + (info.problems === 1 ? "" : "s") + " found" + (age > 30 ? " &middot; not updating" : "");
  }
  document.getElementById("waiting").style.display = any ? "none" : "";
}

function tick() {
  var st = window.liveStatus || {};
  for (var w = 0; w < WORKERS; w++) {
    loadStatus(w);
    if (st[w]) refreshImage(panel(w), w);
  }
  render();
}

function fastTick() {  // the normal-speed emulator's picture, ~15 times a second
  var st = window.liveStatus || {};
  for (var w = 0; w < WORKERS; w++) {
    if (st[w] && st[w].normal_speed) refreshImage(panel(w), w);
  }
}

tick();
setInterval(tick, 1000);
setInterval(fastTick, 66);
</script>
</body></html>
"""


def write_live_page(out: Path, workers: int) -> Path:
    out = Path(out)
    (out / "live").mkdir(parents=True, exist_ok=True)
    path = out / "live.html"
    path.write_text(PAGE.replace("__WORKERS__", str(int(workers))))
    return path
