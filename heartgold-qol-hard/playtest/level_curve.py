"""The level curve: what level a player's team reaches by each boss without grinding.

    python level_curve.py TREE DUMP

TREE is the hack's hg-engine tree, DUMP the unmodified one (as for tools/spoiler_guide.py). The story is split
into stretches, one per boss, each with the maps a player passes through on the way (STRETCHES). Every trainer
standing on those maps is beaten once, in order, and the boss at the end of the stretch too; trainers far above
the stretch's boss are left out (they are rematch or post-game teams sharing the map). Wild battles are not
counted, except in the grind column.

Experience follows the hack's formula (hg-engine's scaled one, src/battle/battle_script_commands.c): beating a
Pokemon of level L with base experience b gives b*L/5 * ((2L+10)/(L+Lp+10))^2.5 to a Pokemon of level Lp
(square roots rounded down), and half as much again from a trainer's Pokemon. Checked against the game: a Violet
Gym trainer's Spearow and Falkner's team, beaten in the emulator, gave within 1% of this.

Ways of sharing it out:

- even: six Pokemon from the start, each KO going to whichever is lowest, as a player who rotates the team
- carry: one Pokemon takes every KO (the upper bound for a player's strongest)

each for the two common growth rates (medium fast, and medium slow, which the starters use). A second table shows
the even team with experience given out more freely, as possible fixes.
"""
import os
import re
import sys
from math import isqrt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))

# the story in order: (boss trainer id, label, maps passed on the way). A rival is fought as the
# Cyndaquil-starter version; the teams are the same levels whichever starter was picked
STRETCHES = [
    (20, "Falkner", ["R30", "R31", "D15R0101", "D15R0102", "D15R0103", "T22GYM0101"]),
    (486, "Proton, Slowpoke Well", ["R32", "D25R0101", "R33", "D26R0102"]),
    (21, "Bugsy", ["T23GYM0102"]),
    (269, "Rival, Azalea", []),
    (30, "Whitney", ["R34", "D37R0102", "T25GYM0101"]),
    (270, "Rival, Burned Tower", ["R35", "D22R0101", "R36", "R37", "D18R0101"]),
    (31, "Morty", ["T27GYM0101"]),
    (34, "Chuck", ["R38", "R39", "D27R0102", "D27R0104", "D27R0105", "D27R0106", "W40", "W41", "T24GYM0101"]),
    (33, "Jasmine", []),
    (488, "Petrel, Rocket HQ", ["R42", "D38R0102", "R43", "T29", "D35R0102", "D35R0103"]),
    (479, "Ariana, Rocket HQ", ["D35R0104"]),
    (32, "Pryce", ["T28GYM0102", "T28GYM0101"]),
    (706, "Proton, Radio Tower", ["D23R0102", "D23R0103", "D23R0104"]),
    (487, "Petrel, Radio Tower", ["D23R0105"]),
    (271, "Rival, Goldenrod Tunnel", ["D37R0104"]),
    (478, "Ariana, Radio Tower", ["D37R0105"]),
    (485, "Archer, Radio Tower", []),
    (35, "Clair", ["R44", "T30GYM0101"]),
    (272, "Rival, Victory Road", ["D44R0102", "R45", "R46", "R27", "R26"]),
    (245, "Will", []),
    (247, "Koga", []),
    (418, "Bruno", []),
    (246, "Karen", []),
    (244, "Lance", []),
]
# a trainer on a stretch's maps more than this many levels above the stretch's boss belongs to later
SLACK = 3
# the chance of each of the 12 grass slots (Day species)
SLOT_ODDS = [20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1]

GROWTH = {
    "medium fast": lambda n: n ** 3,
    "medium slow": lambda n: int(1.2 * n ** 3 - 15 * n ** 2 + 100 * n - 140) if n > 1 else 0,
}
# possible fixes: the even team with experience given out more freely
FIXES = [("Modern Exp. Share", dict(share=True)), ("Double experience", dict(boost=2)),
         ("1.5x experience", dict(boost=1.5))]


def exp_gain(base, level, lp, trainer=True):
    """The hack's scaled formula, in the game's integer steps."""
    total = base * level // 5
    top = (2 * level + 10) ** 2 * isqrt(2 * level + 10)
    bottom = (level + lp + 10) ** 2 * isqrt(level + lp + 10)
    gain = total * top // bottom
    return gain * 3 // 2 if trainer else gain


class Mon:
    def __init__(self, curve, level=5):
        self.curve, self.level, self.exp = curve, level, curve(level)

    def gain(self, n):
        self.exp += n
        while self.level < 100 and self.exp >= self.curve(self.level + 1):
            self.level += 1


def stretches(d):
    """[(label, boss party, [trainer parties on the way], grass slots)], trainers beaten once each."""
    placed = {}
    for code, events in d.events.items():
        for e in events.get("object_events", []):
            m = re.match(r"TRAINER_(\w+) - 1 \+ _std_(\w+)", str(e.get("script", "")))
            if m and m.group(1) in d.trainer_ids and d.trainer_ids[m.group(1)] in d.trainers:
                placed.setdefault(code, []).append(d.trainer_ids[m.group(1)])
    grass = {}
    for t in d.encounters:
        if t["land"]:
            grass.setdefault(t["code"], list(zip(t["levels"], t["land"]["Day"], SLOT_ODDS)))
    seen, out, pool = set(), [], []
    for boss, label, maps in STRETCHES:
        pool = [slot for code in maps for slot in grass.get(code, [])] or pool       # else the last stretch's
        top = max(p["level"] for p in d.trainers[boss]["party"])
        way = []
        for code in maps:
            for t in dict.fromkeys(placed.get(code, [])):
                party = d.trainers[t]["party"]
                if t not in seen and max(p["level"] for p in party) <= top + SLACK:
                    seen.add(t)
                    way.append(party)
        out.append((label, d.trainers[boss]["party"], way, pool))
    return out


def run(plan, base, curve, mode, grind=False, share=False, boost=1):
    """For each boss: (label, lowest, highest level of the team on arrival, trainers on the way, wild KOs).
    With grind, wild Pokemon of the stretch's grass (each worth the slots' average) are beaten until the team's
    lowest is at the boss's average level."""
    team = [Mon(curve) for _ in range(6 if mode == "even" else 1)]
    rows = []

    def beat(party):
        for p in party:
            m = min(team, key=lambda x: (x.level, x.exp))
            got = {m: exp_gain(base.get(p["species"], 0), p["level"], m.level) * boost}
            if share:            # the rest of the party half as much, each at its own level
                for o in team:
                    if o is not m:
                        got[o] = exp_gain(base.get(p["species"], 0), p["level"], o.level) * boost / 2
            for o, n in got.items():
                o.gain(int(n))

    def wild(m, pool):
        total = sum(odds for _, _, odds in pool)
        return sum(odds * exp_gain(base.get(s, 0), lv, m.level, trainer=False) for lv, s, odds in pool) // total

    for label, boss, way, pool in plan:
        for party in way:
            beat(party)
        kos = 0
        target = round(sum(p["level"] for p in boss) / len(boss))
        while grind and pool and min(m.level for m in team) < target:
            m = min(team, key=lambda x: (x.level, x.exp))
            m.gain(max(1, wild(m, pool)))
            kos += 1
        rows.append((label, min(m.level for m in team), max(m.level for m in team), len(way), kos))
        beat(boss)
    return rows


def span(row):
    return "%d" % row[1] if row[1] == row[2] else "%d-%d" % (row[1], row[2])


def main():
    import spoiler_guide
    tree, dump = sys.argv[1], sys.argv[2]
    d = spoiler_guide.Data(tree, dump)
    base = {k: int(v) for k, v in re.findall(r"\[SPECIES_(\w+)\s*\] = (\d+)", d.read("data/BaseExperienceTable.c"))}
    plan = stretches(d)
    even = {g: run(plan, base, GROWTH[g], "even") for g in GROWTH}
    carry = {g: run(plan, base, GROWTH[g], "carry") for g in GROWTH}
    grinds = {g: run(plan, base, GROWTH[g], "even", grind=True) for g in GROWTH}
    print("| Boss | Their levels | Trainers on the way | Even team, medium fast | Even team, medium slow "
          "| One carry, medium fast | One carry, medium slow | Wild KOs to reach their average, medium fast "
          "| The same, medium slow |")
    print("|---|---|---|---|---|---|---|---|---|")
    for i, (label, boss, way, pool) in enumerate(plan):
        levels = [p["level"] for p in boss]
        cells = [span(even[g][i]) for g in GROWTH] + ["%d" % carry[g][i][2] for g in GROWTH] + \
                ["%d" % grinds[g][i][4] for g in GROWTH]
        print("| %s | %d-%d (avg %.0f) | %d | %s |" % (label, min(levels), max(levels), sum(levels) / len(levels),
                                                    len(way), " | ".join(cells)))
    for g in GROWTH:
        print("wild KOs in all, %s: %d" % (g, sum(r[4] for r in grinds[g])))
    print()
    print("| Boss | Their average | " + " | ".join("%s, %s" % (f, g) for f, _ in FIXES for g in GROWTH) + " |")
    print("|---|---|" + "---|" * (len(FIXES) * len(GROWTH)))
    fixed = {(f, g): run(plan, base, GROWTH[g], "even", **kw) for f, kw in FIXES for g in GROWTH}
    for i, (label, boss, way, pool) in enumerate(plan):
        avg = sum(p["level"] for p in boss) / len(boss)
        print("| %s | %.0f | %s |" % (label, avg, " | ".join(span(fixed[(f, g)][i]) for f, _ in FIXES for g in GROWTH)))


if __name__ == "__main__":
    main()
