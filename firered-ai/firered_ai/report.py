"""The playtest report: report.html and summary.json in the run folder."""

from __future__ import annotations

import html
import json
import time
from pathlib import Path

from . import checklist, story
from .explorer import CHECK_BUDGET, STORY_BUDGET
from .game import Game

SEVERITY = {"setup": -1, "crash": 0, "softlock": 1, "corrupt": 2, "rule": 3, "feature": 4}
KIND_LABEL = {"setup": "Playtester setup", "crash": "Crash", "softlock": "Softlock", "corrupt": "Corrupt data",
              "rule": "Rule broken", "feature": "Hack feature"}
# Maps that exist but aren't normally reachable (link rooms, unused, event-only).
UNREACHABLE_PREFIXES = ("BattleColosseum", "TradeCenter", "RecordCorner", "UnionRoom", "Unused", "BirthIsland",
                        "NavelRock", "SevenIsland_TanobyRuins_", "SixIsland_AlteringCave")
SPIKE_MIN_BLACKOUTS = 3
SPIKE_RATE = 0.25


def collect(out: Path) -> dict:
    config = json.loads((out / "config.json").read_text())
    game = Game.load(config["game"])
    findings = []
    for f in sorted(out.glob("findings-w*.jsonl")):
        for line in f.read_text().splitlines():
            try:
                findings.append(json.loads(line))
            except ValueError:
                pass
    groups: dict[str, dict] = {}
    for rec in findings:
        g = groups.setdefault(rec["signature"], {"first": rec, "count": 0, "folders": [], "reproduced": None})
        g["count"] += 1
        if rec.get("folder"):
            g["folders"].append(rec["folder"])
        r = rec.get("extra", {}).get("reproduced")
        if r is not None:
            g["reproduced"] = bool(g["reproduced"]) or r
    stats = []
    for f in sorted(out.glob("stats-w*.json")):
        try:
            stats.append(json.loads(f.read_text()))
        except ValueError:
            pass
    total = {"steps": 0, "sessions": 0, "maps": {}, "trainers_beaten": {}, "seen": set(), "owned": set(),
             "battles": {}, "blackouts": [], "starts": {}, "session_ends": [], "story_stalls": {}, "checklist": {}}
    for st in stats:
        total["steps"] += st["steps"]
        total["sessions"] += st["sessions"]
        for k in ("maps", "trainers_beaten", "starts", "story_stalls"):
            for name, n in st.get(k, {}).items():
                total[k][name] = total[k].get(name, 0) + n
        total["seen"] |= set(st["species_seen"])
        total["owned"] |= set(st["species_owned"])
        for name, b in st["battles"].items():
            t = total["battles"].setdefault(name, {"wild": 0, "trainer": 0, "blackouts": 0, "trainer_losses": 0,
                                                   "lost_no_blackout": 0})
            for k, v in b.items():
                t[k] = t.get(k, 0) + v
        total["blackouts"] += st["blackouts"]
        for key, c in st.get("checklist", {}).items():
            t = total["checklist"].setdefault(key, {"pass": 0, "fail": 0, "unreached": 0})
            for k, v in c.items():
                t[k] = t.get(k, 0) + v
        total["session_ends"] += st.get("session_ends", [])
    furthest = []
    for f in sorted(out.glob("furthest/w*.json")):
        try:
            furthest.append({**json.loads(f.read_text()), "file": f"furthest/{f.stem}.state"})
        except ValueError:
            pass
    return {"config": config, "game": game, "groups": groups, "total": total, "furthest": furthest}


def progress_summary(ends: list) -> dict:
    """Where sessions finished: how many had each number of badges, and the usual last maps."""
    if not ends:
        return {"sessions": 0}
    badges: dict[int, int] = {}
    maps: dict[str, int] = {}
    objectives: dict[str, int] = {}
    for e in ends:
        badges[e["badges"]] = badges.get(e["badges"], 0) + 1
        maps[e["map"]] = maps.get(e["map"], 0) + 1
        if e.get("objective"):
            objectives[e["objective"]] = objectives.get(e["objective"], 0) + 1
    return {
        "sessions": len(ends),
        "average_badges": round(sum(e["badges"] for e in ends) / len(ends), 1),
        "average_top_level": round(sum(e["top_level"] for e in ends) / len(ends)),
        "badges": dict(sorted(badges.items())),
        "common_maps": sorted(maps.items(), key=lambda kv: -kv[1])[:8],
        "objectives": sorted(objectives.items(), key=lambda kv: -kv[1])[:8],
    }


def summarize(data: dict) -> dict:
    game, total, groups = data["game"], data["total"], data["groups"]
    reachable = [m["name"] for m in game.p["maps"] if not m["name"].startswith(UNREACHABLE_PREFIXES)]
    visited = set(total["maps"])
    fightable = game.fightable_trainers
    beaten = {int(t) for t in total["trainers_beaten"]}
    spikes = []
    for name, b in total["battles"].items():
        n = b["wild"] + b["trainer"]
        if b["blackouts"] >= SPIKE_MIN_BLACKOUTS and n and b["blackouts"] / n >= SPIKE_RATE:
            spikes.append({"map": name, **b, "rate": round(b["blackouts"] / n, 2)})
    spikes.sort(key=lambda x: -x["blackouts"])
    found = sorted(groups.values(), key=lambda g: (SEVERITY.get(g["first"]["kind"], 9), -g["count"]))
    elapsed = time.time() - data["config"]["started"]
    return {
        "game": data["config"]["rom_note"],
        "elapsed_hours": round(elapsed / 3600, 2),
        "presses": total["steps"],
        "game_hours": round(total["steps"] * 30 / 60 / 3600, 1),  # ~30 frames a press
        "sessions": total["sessions"],
        "findings": [{"kind": g["first"]["kind"], "title": g["first"]["title"], "map": g["first"]["map"],
                      "detail": g["first"]["detail"], "count": g["count"], "reproduced": g["reproduced"],
                      "folders": g["folders"]} for g in found],
        "maps_visited": len(visited & set(reachable)),
        "maps_total": len(reachable),
        "maps_never": sorted(set(reachable) - visited),
        "trainers_beaten": len(beaten & set(fightable)),
        "trainers_total": len(fightable),
        "species_seen": len(total["seen"]),
        "species_owned": len(total["owned"]),
        "dex_count": game.p["dex_count"],
        "blackouts": len(total["blackouts"]),
        "battles": total["battles"],
        "difficulty_spikes": spikes,
        "starts": total["starts"],
        "furthest": sorted(data["furthest"], key=lambda f: (f["champion"], f["badges"], f.get("story_done", 0),
                                                            f["top_level"], f["dex_owned"]), reverse=True),
        "checklist": checklist_rows(total["checklist"], checklist.is_hack(game)),
        "story_stalls": sorted(total["story_stalls"].items(), key=lambda kv: -kv[1]),
        "story_total": sum(1 for o in story.STORY if not o.post_game),
        "session_ends": progress_summary(total["session_ends"]),
        "continued_from": data["config"].get("continued_from"),
    }


CSS = """
:root { --bg:#fbfbfa; --fg:#1d1d1b; --muted:#6b6b66; --line:#e4e3df; --card:#fff;
        --crash:#b3261e; --softlock:#b86e00; --corrupt:#7b3fbf; --rule:#1f6fb2; --ok:#2e7d32; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#161615; --fg:#ecebe8;
        --muted:#a3a29d; --line:#33322f; --card:#1f1f1d; --crash:#ff8a80; --softlock:#ffb74d; --corrupt:#ce93d8;
        --rule:#90caf9; --ok:#81c784; } }
body { background:var(--bg); color:var(--fg); font:15px/1.5 system-ui, sans-serif; margin:0; padding:24px 16px; }
main { max-width:960px; margin:0 auto; }
h1 { font-size:24px; margin:0 0 4px; } h2 { font-size:18px; margin:32px 0 8px; }
.muted { color:var(--muted); } .tiles { display:flex; flex-wrap:wrap; gap:12px; margin:16px 0; }
.tile { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:10px 14px; min-width:120px; }
.tile b { display:block; font-size:20px; }
table { width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line); border-radius:10px; }
th, td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:top; }
th { font-size:13px; color:var(--muted); font-weight:600; }
.kind { font-weight:600; white-space:nowrap; } .crash{color:var(--crash)} .softlock{color:var(--softlock)}
.corrupt{color:var(--corrupt)} .rule{color:var(--rule)} .ok{color:var(--ok)} .setup{color:var(--muted)} .feature{color:var(--softlock)}
img { max-width:240px; border-radius:6px; border:1px solid var(--line); image-rendering:pixelated; }
details summary { cursor:pointer; } code { font-size:13px; }
.wrap { overflow-x:auto; }
"""


def data_battles(s: dict):
    return s.get("battles", {}).items()


def progress_html(s: dict) -> str:
    e = html.escape
    parts = ["<h2>How far it got</h2>"]
    if s.get("continued_from"):
        parts.append(f'<p class="muted">This run carried on from {e(str(s["continued_from"]))}.</p>')
    if s["furthest"]:
        f = s["furthest"][0]
        where = "became Champion" if f["champion"] else f'{f["badges"]} badge{"" if f["badges"] == 1 else "s"}'
        if f.get("story_done"):
            where += f', {f["story_done"]} of {s.get("story_total", "?")} story objectives'
        parts.append(
            f'<p><b>Furthest point:</b> {e(where)}, on {e(f["map"].replace("_", " "))}, with '
            f'{e(", ".join(f["party"]))} ({f["dex_owned"]} species caught). '
            f'It started that session from {e(f["start"])}.</p>'
            f'<p class="muted">A save state of that moment is <a href="{e(f["file"])}">{e(f["file"])}</a> in this run\'s '
            "folder. Load it in mGBA (File &rarr; Load State File) to see it or to make a save there. "
            "Choose <i>Carry on from the last run</i> next time to keep going from it.</p>")
    else:
        parts.append("<p>Nothing yet.</p>")
    se = s["session_ends"]
    if se.get("sessions"):
        counts = " &middot; ".join(f"{b} badge{'' if b == 1 else 's'}: {n}" for b, n in se["badges"].items())
        common = ", ".join(f"{e(m.replace('_', ' '))} ({n})" for m, n in se["common_maps"])
        parts.append(
            f'<p><b>Where sessions ended</b> ({se["sessions"]} sessions): on average {se["average_badges"]} badges '
            f'and a strongest Pokémon of Lv. {se["average_top_level"]}.<br>{counts}</p>'
            f'<p class="muted">Most common last maps: {common}</p>')
        if se.get("objectives"):
            stuck = ", ".join(f"{e(title(k))} ({n})" for k, n in se["objectives"])
            parts.append(f'<p><b>Story objective they were on</b> when sessions ended: {stuck}</p>')
    if s.get("story_stalls"):
        stalls = ", ".join(f"{e(title(k))} ({n}&times;)" for k, n in s["story_stalls"])
        parts.append(f'<p><b>Story objectives it got stuck on</b> (worked on for {CHECK_BUDGET:,} to {STORY_BUDGET:,} '
                     f'presses without getting done, then put aside for a while): {stalls}</p>'
                     '<p class="muted">An objective high on this list may be a story bug (a flag that never '
                     "gets set, an event that won't start), or just a puzzle the playtester can't do.</p>")
    return "\n".join(parts)


def checklist_rows(counts: dict, hack: bool = True) -> list[dict]:
    """Every checklist item, in order, with what happened to it across all workers."""
    rows = [{"key": c.key, "title": c.title, "part": c.part, "why": c.why, "post_game": c.post_game}
            for c in checklist.CHECKS if hack or c.part == "story"]
    if not hack:
        for r in rows:
            r.update(counts.get(r["key"], {"pass": 0, "fail": 0, "unreached": 0}))
        return rows
    rows += [{"key": w.key, "title": w.title, "part": "hack", "why": w.why, "post_game": w.post_game}
             for w in checklist.WATCHES]
    rows += [{"key": k, "title": t, "part": "hack", "why": "HMs work from the overworld", "post_game": False}
             for k, t in checklist.FIELD_MOVES.values()]
    for r in rows:
        r.update(counts.get(r["key"], {"pass": 0, "fail": 0, "unreached": 0}))
    return rows


def checklist_html(s: dict) -> str:
    e = html.escape
    rows = s.get("checklist") or []
    if not rows:
        return ""
    worked = sum(1 for r in rows if r["pass"])
    broken = sum(1 for r in rows if r["fail"])
    out = [f"<h2>Checklist</h2><p>{worked} of {len(rows)} items done at least once"
           f"{f', <b>{broken} that didn\'t work</b> (see Problems found)' if broken else ''}. "
           "Story items count when a worker finished them during the run; hack items when a worker tried the "
           "feature and saw it work.</p>", '<div class="wrap"><table><tr><th>Item</th><th>Part</th>'
           "<th>Result</th></tr>"]
    for r in rows:
        if r["fail"]:
            res = f'<span class="crash">Didn\'t work ({r["fail"]}&times;)</span>'
            if r["pass"]:
                res += f', worked {r["pass"]}&times;'
        elif r["pass"]:
            res = f'<span class="ok">Done ({r["pass"]}&times;)</span>'
        elif r["unreached"]:
            res = "Couldn't get there"
        else:
            res = '<span class="muted">Not reached yet</span>'
        part = "Story" if r["part"] == "story" else "Hack"
        if r["post_game"]:
            part += ", post-game"
        why = f'<br><span class="muted">{e(r["why"])}</span>' if r.get("why") else ""
        out.append(f"<tr><td>{e(r['title'])}{why}</td><td>{part}</td><td>{res}</td></tr>")
    out.append("</table></div>")
    return "\n".join(out)


def title(key: str) -> str:
    return checklist.ALL_TITLES.get(key, key)


def write_report(out: Path) -> Path:
    out = Path(out)
    data = collect(out)
    s = summarize(data)
    (out / "summary.json").write_text(json.dumps(s, indent=1))
    e = html.escape
    rows = []
    for f in s["findings"]:
        media = ""
        if f["folders"]:
            d = f["folders"][0]
            media = (f'<a href="{e(d)}/clip.gif"><img src="{e(d)}/screenshot.png" alt="screenshot"></a><br>'
                     f'<a href="{e(d)}">files</a> · <code>python replay.py ROM {e(d)}</code>')
        rep = {True: '<span class="ok">yes</span>', False: "no", None: "n/a"}[f["reproduced"]]
        rows.append(f'<tr><td class="kind {e(f["kind"])}">{e(KIND_LABEL.get(f["kind"], f["kind"]))}</td>'
                    f'<td><b>{e(f["title"])}</b><br>{e(f["detail"])}<br><span class="muted">{e(f["map"])}</span></td>'
                    f'<td>{f["count"]}</td><td>{rep}</td><td>{media}</td></tr>')
    findings = ("<div class=wrap><table><tr><th>Kind</th><th>What</th><th>Times</th><th>Reproduced</th><th>Evidence</th></tr>"
                + "".join(rows) + "</table></div>") if rows else "<p>No problems found.</p>"
    spikes = "".join(f'<tr><td>{e(x["map"])}</td><td>{x["blackouts"]}</td><td>{x["wild"]}</td><td>{x["trainer"]}</td>'
                     f'<td>{int(x["rate"] * 100)}%</td></tr>' for x in s["difficulty_spikes"])
    spikes = ("<div class=wrap><table><tr><th>Map</th><th>Blackouts</th><th>Wild battles</th><th>Trainer battles</th>"
              f"<th>Blackout rate</th></tr>{spikes}</table></div>") if spikes else "<p>No map stood out.</p>"
    lost = sorted(((n, b["lost_no_blackout"]) for n, b in data_battles(s) if b.get("lost_no_blackout")),
                  key=lambda kv: -kv[1])
    if lost:
        spikes += ('<p class="muted">Battles lost without a blackout (the game carried on, as after the first '
                   "rival battle), not counted above: "
                   + ", ".join(f"{e(n.replace('_', ' '))} ({c})" for n, c in lost) + "</p>")
    never = ", ".join(e(m) for m in s["maps_never"][:400])
    starts = ", ".join(f"{e(k)} ×{v}" for k, v in sorted(s["starts"].items(), key=lambda kv: -kv[1])[:30])
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Playtest Report</title>
<style>{CSS}</style></head><body><main>
<h1>Playtest report</h1>
<p class="muted">{e(s["game"])} · updated {time.strftime("%Y-%m-%d %H:%M")} · {s["elapsed_hours"]} h real time,
about {s["game_hours"]} h of play, {s["presses"]:,} presses, {s["sessions"]} session{"" if s["sessions"] == 1 else "s"}</p>
<div class="tiles">
<div class="tile"><b>{len(s["findings"])}</b>different problems</div>
<div class="tile"><b>{s["maps_visited"]}/{s["maps_total"]}</b>maps visited</div>
<div class="tile"><b>{s["trainers_beaten"]}/{s["trainers_total"]}</b>trainers beaten</div>
<div class="tile"><b>{s["species_owned"]}/{s["dex_count"]}</b>species owned</div>
<div class="tile"><b>{s["blackouts"]}</b>blackouts</div></div>
{progress_html(s)}
<h2>Problems found</h2>
<p class="muted">Worst first. "Reproduced" means replaying the same presses from the saved state shortly before
caused it again. Click a screenshot for a clip of the lead-up.</p>
{findings}
<h2>Possible difficulty spikes</h2>
<p class="muted">Maps with at least {SPIKE_MIN_BLACKOUTS} blackouts and a blackout rate of
{int(SPIKE_RATE * 100)}% or more. The tester battles with simple rules (the move that does the most damage), so
treat this as a pointer, not a verdict.</p>
{spikes}
{checklist_html(s)}
<h2>Coverage</h2>
<details><summary>{len(s["maps_never"])} reachable maps not visited yet</summary><p>{never}</p></details>
<details><summary>Where sessions started</summary><p>{starts}</p></details>
</main></body></html>"""
    path = out / "report.html"
    tmp = out / "report.tmp"
    tmp.write_text(page)
    tmp.replace(path)
    return path
