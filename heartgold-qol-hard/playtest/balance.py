"""Boss balance summary from the story bot's battle records.

    python3 balance.py [results/battles.jsonl] [--run PREFIX] [--exclude PREFIX]

--run keeps only the records whose run label starts with PREFIX (for example rebalance-0022); --exclude
drops them, which leaves the records from before.

Prints a Markdown table: for each boss fight (trainer and map), the battles
fought, the wins, how many of ours fainted in a win, and which of the boss's
Pokemon knocked ours out. The records come from every run kept, with
different team sets and bot fixes along the way, so read a rate as a rough
signal, not a measurement.
"""
import json
import sys
from collections import Counter, OrderedDict

BOSS_CLASSES = ("LEADER", "ELITE_FOUR", "CHAMPION", "EXECUTIVE", "RIVAL", "KIMONO")


def load(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def summary(records):
    fights = OrderedDict()
    for r in records:
        if not r["trainers"] or not r["trainers"][0]["cls"].startswith(BOSS_CLASSES):
            continue
        t = r["trainers"][0]
        fights.setdefault((t["name"], r["at"][0]), []).append(r)
    rows = []
    for (name, where), battles in fights.items():
        won = [b for b in battles if b["result"] == "won"]
        # a few records name a Pokemon by a large number, a misread after the battle: count only named ones
        fainted = [sum(k["side"] == "player" and isinstance(k["fainted"], str) for k in b["kos"]) for b in won]
        by = Counter(k["by"] for b in battles for k in b["kos"] if k["side"] == "player" and isinstance(k.get("by"), str) and k["by"])
        rows.append(dict(name=name, where=where, battles=len(battles), won=len(won),
                         fainted=sum(fainted) / len(fainted) if fainted else None, by=by))
    return rows


def markdown(rows):
    out = ["| Boss | Map | Won | Ours fainted per win | Knocked ours out |", "|---|---|---|---|---|"]
    for r in rows:
        rate = "%d of %d (%d%%)" % (r["won"], r["battles"], round(100 * r["won"] / r["battles"]))
        fainted = "%.1f" % r["fainted"] if r["fainted"] is not None else "—"
        by = ", ".join("%s %d" % (s.title(), n) for s, n in r["by"].most_common(4)) or "—"
        out.append("| %s | %s | %s | %s | %s |" % (r["name"], r["where"], rate, fainted, by))
    return "\n".join(out)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("path", nargs="?", default="results/battles.jsonl")
    p.add_argument("--run", action="append", default=[])
    p.add_argument("--exclude", action="append", default=[])
    a = p.parse_args()
    records = load(a.path)
    if a.run:
        records = [r for r in records if str(r.get("run")).startswith(tuple(a.run))]
    if a.exclude:
        records = [r for r in records if not str(r.get("run")).startswith(tuple(a.exclude))]
    print(markdown(summary(records)))
