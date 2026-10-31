#!/usr/bin/env python3
"""Modernization pass for the FireRed QoL+Hard hack.

Reads Pokemon Showdown's data/{moves,pokedex,learnsets}.ts as *text* (they are
never executed) and updates the decomp's data:

  * src/data/battle_moves.h   - adds .split (physical/special/status) to every
                                move, and updates power/accuracy/PP to modern
                                values where the Gen 3 effect is compatible.
  * src/data/pokemon/species_info.h     - modern base stats.
  * src/data/pokemon/level_up_learnsets.h - newest level-up learnsets
                                (Gen 9 > 8 > 7), limited to Gen 1-3 moves.

Usage (from the repo root, on a checkout without these changes applied):
    python3 tools/hack/modernize.py /path/to/pokemon-showdown/data
"""
import re
import sys

SD = sys.argv[1]
GEN3_MOVES = 354

def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())

def ts_entries(path):
    """Yield (key, [lines]) for each top-level entry of a Showdown data table."""
    key, body = None, []
    for line in open(path, encoding="utf-8"):
        m = re.match(r'^\t"?(\w+)"?: \{$', line.rstrip("\n"))
        if m:
            key, body = m.group(1), []
        elif line.startswith("\t},") and key:
            yield key, body
            key = None
        elif key:
            body.append(line.rstrip("\n"))

def field(body, name):
    for line in body:
        m = re.match(r"^\t\t%s: (.*),$" % name, line)
        if m:
            return m.group(1)
    return None

# ---------------------------------------------------------------- constants
def read_defines(path, prefix):
    out = {}
    for m in re.finditer(r"#define (%s\w+)\s+(\d+)" % prefix, open(path).read()):
        out[m.group(1)] = int(m.group(2))
    return out

move_consts = read_defines("include/constants/moves.h", "MOVE_")
move_by_num = {v: k for k, v in move_consts.items() if 0 < v <= GEN3_MOVES}

# ---------------------------------------------------------------- moves
sd_moves = {}          # num -> dict
sd_move_num = {}       # showdown id -> num
for key, body in ts_entries(SD + "/moves.ts"):
    num = field(body, "num")
    if num is None or not num.isdigit():
        continue
    num = int(num)
    sd_move_num[key] = num
    if num > GEN3_MOVES or key != norm(key):
        continue
    sd_moves[num] = {
        "power": field(body, "basePower"),
        "acc": field(body, "accuracy"),
        "pp": field(body, "pp"),
        "cat": (field(body, "category") or '"Status"').strip('"'),
    }

SPLIT = {"Physical": "SPLIT_PHYSICAL", "Special": "SPLIT_SPECIAL", "Status": "SPLIT_STATUS"}
changes = []

def patch_move(m):
    const, body = m.group(1), m.group(2)
    num = move_consts.get(const, 0)
    sd = sd_moves.get(num)
    if sd is None:  # MOVE_NONE
        split = "SPLIT_PHYSICAL"
    else:
        split = SPLIT[sd["cat"]]
        old_power = int(re.search(r"\.power = (\d+)", body).group(1))
        old_acc = int(re.search(r"\.accuracy = (\d+)", body).group(1))
        # Only touch fixed-power moves; power 0/1 are status or computed in code.
        if old_power > 1 and sd["power"] and sd["power"].isdigit() and 1 < int(sd["power"]) <= 255:
            if int(sd["power"]) != old_power:
                changes.append(f"{const}: power {old_power} -> {sd['power']}")
            body = re.sub(r"\.power = \d+", ".power = " + sd["power"], body)
        # 0 accuracy means "never misses" in Gen 3; leave those alone.
        if old_acc and sd["acc"] and sd["acc"].isdigit() and int(sd["acc"]) != old_acc:
            changes.append(f"{const}: accuracy {old_acc} -> {sd['acc']}")
            body = re.sub(r"\.accuracy = \d+", ".accuracy = " + sd["acc"], body)
        if sd["pp"] and sd["pp"].isdigit():
            body = re.sub(r"\.pp = \d+", ".pp = " + sd["pp"], body)
    body = re.sub(r"(\n(\s*)\.flags = [^\n]*\n)", r"\1\2.split = %s,\n" % split, body)
    return "[%s] =%s" % (const, body)

p = "src/data/battle_moves.h"
s = open(p).read()
s, n = re.subn(r"\[(MOVE_\w+)\] =(\s*\{.*?\n    \},)", patch_move, s, flags=re.S)
assert n == GEN3_MOVES + 1, n
open(p, "w").write(s)

# ---------------------------------------------------------------- species
species = [k for k in read_defines("include/constants/species.h", "SPECIES_")
           if not k.startswith(("SPECIES_OLD_UNOWN", "SPECIES_UNOWN_")) and k not in
           ("SPECIES_NONE", "SPECIES_EGG", "NUM_SPECIES")]
sd_dex = {key: body for key, body in ts_entries(SD + "/pokedex.ts")}
missing = [sp for sp in species if norm(sp[8:]) not in sd_dex]

STATS = [("hp", "baseHP"), ("atk", "baseAttack"), ("def", "baseDefense"),
         ("spe", "baseSpeed"), ("spa", "baseSpAttack"), ("spd", "baseSpDefense")]
p = "src/data/pokemon/species_info.h"
s = open(p).read()
for sp in species:
    body = sd_dex.get(norm(sp[8:]))
    if body is None:
        continue
    bs = dict(re.findall(r"(\w+): (\d+)", field(body, "baseStats")))
    def fix(m):
        block = m.group(0)
        for sdk, fld in STATS:
            old = re.search(r"\.%s = (\d+)" % fld, block).group(1)
            if old != bs[sdk]:
                changes.append(f"{sp}: {fld} {old} -> {bs[sdk]}")
            block = re.sub(r"\.%s = \d+" % fld, ".%s = %s" % (fld, bs[sdk]), block)
        return block
    s, n = re.subn(r"\[%s\] =\s*\{.*?\n    \}," % sp, fix, s, count=1, flags=re.S)
    assert n == 1, sp
open(p, "w").write(s)

# ---------------------------------------------------------------- learnsets
sd_learn = {}
for key, body in ts_entries(SD + "/learnsets.ts"):
    moves = {}
    for line in body:
        m = re.match(r"^\t\t\t(\w+): \[(.*)\],$", line)
        if m:
            moves[m.group(1)] = re.findall(r'"(\d+)L(\d+)"', m.group(2))
    sd_learn[key] = moves

ptrs = dict(re.findall(r"\[(SPECIES_\w+)\] = (s\w+LevelUpLearnset)",
                       open("src/data/pokemon/level_up_learnset_pointers.h").read()))
p = "src/data/pokemon/level_up_learnsets.h"
s = open(p).read()
done = set()
for sp in species:
    arr = ptrs.get(sp)
    learn = sd_learn.get(norm(sp[8:]))
    if not arr or not learn or arr in done:
        continue
    gens = {g for entries in learn.values() for g, _ in entries}
    gen = max((g for g in gens if g in "789"), default=None)
    if gen is None:
        continue
    pairs = set()
    for mv, entries in learn.items():
        num = sd_move_num.get(mv)
        if num is None or num > GEN3_MOVES:
            continue
        for g, lvl in entries:
            if g == gen:
                pairs.add((max(1, int(lvl)), num))
    if not pairs:
        continue
    lines = [f"static const u16 {arr}[] = {{"]
    lines += [f"    LEVEL_UP_MOVE({l}, {move_by_num[n]})," for l, n in sorted(pairs)]
    lines += ["    LEVEL_UP_END", "};"]
    s, n = re.subn(r"static const u16 %s\[\] = \{.*?\n\};" % arr, "\n".join(lines), s, flags=re.S)
    assert n >= 1, arr
    done.add(arr)
open(p, "w").write(s)

open("tools/hack/modernize_changes.txt", "w").write("\n".join(changes) + "\n")
print(f"moves updated, {len(done)} learnsets replaced, unmatched species: {missing}")
