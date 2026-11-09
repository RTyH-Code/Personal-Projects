#!/usr/bin/env python3
"""Late-game trainer Pokemon evolve where their level allows.

The post-game level scaling (postgame_levels.py) skipped an evolution when
the evolved species was already on the team, which left teams like a Lv. 72
Mareep next to an Ampharos, or five Lv. 68 Magikarp. This evolves every
trainer Pokemon of Lv. 50 or higher that is at least 5 levels past a
level-up evolution, step by step along its family (duplicates are allowed,
as in the original game). A second run (release 21) adds the classic
Gen 1-3 stone, item, trade and friendship evolutions for Lv. 50+ trainers;
later-generation ones (Rhyperior, Magnezone, ...) are left alone below Lv. 75;
a third run (release 22) gives them to the Lv. 75+ teams only. Early and
mid-game teams keep their classic unevolved Pokemon. Custom movesets are
kept. Each pass runs once.
"""
import os, re, subprocess, sys

os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MIN_LEVEL, GRACE = 50, 5
MARK = "// FireRed QoL+Hard: late-game evolutions (tools/hack/trainer_evolutions.py)\n"
ITEM_MARK = "// FireRed QoL+Hard: late-game stone and item evolutions (tools/hack/trainer_evolutions.py)\n"
TOP_MARK = "// FireRed QoL+Hard: later-generation evolutions for Lv. 75+ (tools/hack/trainer_evolutions.py)\n"
TOP_LEVEL = 75


def read(p):
    return open(p, encoding="utf-8").read()


tp = read("src/data/trainer_parties.h")
done_level = MARK in tp
done_item = ITEM_MARK in tp
if done_level and done_item and TOP_MARK in tp:
    sys.exit("Late-game trainer Pokemon are already evolved.")

# Classic (Gen 1-3) evolutions by stone, held item, trade or friendship:
# a Lv. 50+ trainer's Pokemon has them. Later-generation evolutions
# (Rhyperior, Magnezone, ...) need badge-gated items, so they're left alone.
CLASSIC = set(re.findall(r"#define (SPECIES_\w+) ", subprocess.run(
    ["git", "show", "ce6406d:include/constants/species.h"], capture_output=True, text=True).stdout))
item_evo, any_evo = {}, {}
for sp, body in re.findall(r"\[(SPECIES_\w+)\]\s*=\s*\{(.*?)\}\},", read("src/data/pokemon/evolution.h"), re.S):
    for method, param, target in re.findall(r"\{(EVO_\w+), ([^,]+), (SPECIES_\w+)", body):
        if not method.startswith("EVO_LEVEL") and target in CLASSIC and sp in CLASSIC:
            item_evo.setdefault(sp, target)
        if not method.startswith("EVO_LEVEL"):
            any_evo.setdefault(sp, target)

level_evo = {}
for sp, body in re.findall(r"\[(SPECIES_\w+)\]\s*=\s*\{(.*?)\}\},", read("src/data/pokemon/evolution.h"), re.S):
    for method, param, target in re.findall(r"\{(EVO_LEVEL\w*), (\d+), (SPECIES_\w+)", body):
        if method != "EVO_LEVEL_SHEDINJA":
            level_evo.setdefault(sp, (int(param), target))


def evolve(sp, lvl):
    for _ in range(3):
        if not done_level and sp in level_evo and lvl >= level_evo[sp][0] + GRACE:
            sp = level_evo[sp][1]
        elif not done_item and sp in item_evo:
            sp = item_evo[sp]
        elif done_item and lvl >= TOP_LEVEL and sp in any_evo:
            sp = any_evo[sp]
        else:
            break
    return sp


changes = []


def do_mon(m):
    mon = m.group(0)
    lvl = int(re.search(r"\.lvl = (\d+)", mon).group(1))
    sp = re.search(r"\.species = (SPECIES_\w+)", mon).group(1)
    to = evolve(sp, lvl) if lvl >= MIN_LEVEL else sp
    if to == sp:
        return mon
    changes.append(f"Lv. {lvl} {sp[8:]} -> {to[8:]}")
    return mon.replace(f".species = {sp}", f".species = {to}")


def do_party(m):
    before = len(changes)
    body = re.sub(r"    \{\n.*?\n    \}", do_mon, m.group(2), flags=re.S)
    if len(changes) == before:
        return m.group(0)
    mark = TOP_MARK if done_item else ITEM_MARK if done_level else MARK
    return mark + m.group(1) + body + m.group(3)


tp = re.sub(r"(static const struct \w+ sParty_\w+\[\] = \{\n)(.*?)(\n\};\n)", do_party, tp, flags=re.S)
open("src/data/trainer_parties.h", "w", encoding="utf-8").write(tp)
print("\n".join(changes))
print(f"\n{len(changes)} trainer Pokemon evolved.")
