#!/usr/bin/env python3
"""Post-game difficulty: bridge the first Champion (Lv. 66-72) and the round 2
Elite Four (Lv. 72-86).

  - Sevii Islands 4-7 trainers (and their VS Seeker rematch teams): 1.3x
  - Post-game VS Seeker rematch teams on other routes (the tiers that unlock
    after the Champion): 1.25x
  - Sevii Islands 4-7 wild Pokemon: 1.35x (fishing levels unchanged)
Trainer Pokemon evolve where the new level allows, without duplicating a
species already on that team. The Trainer Tower is separate (it scales to
your level). Runs once.
"""
import glob, json, os, re, sys

os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SEVII_TRAINERS, POSTGAME_REMATCH, SEVII_WILD = 1.3, 1.25, 1.35
ISLANDS = ("FourIsland", "FiveIsland", "SixIsland", "SevenIsland")
ISLAND_MAPS = ("FOUR_ISLAND", "FIVE_ISLAND", "SIX_ISLAND", "SEVEN_ISLAND")
STONE = {"VULPIX": "NINETALES", "CLEFAIRY": "CLEFABLE", "JIGGLYPUFF": "WIGGLYTUFF", "WEEPINBELL": "VICTREEBEL",
         "POLIWHIRL": "POLIWRATH", "GROWLITHE": "ARCANINE", "EXEGGCUTE": "EXEGGUTOR", "SHELLDER": "CLOYSTER",
         "STARYU": "STARMIE", "GLOOM": "VILEPLUME", "NIDORINA": "NIDOQUEEN", "NIDORINO": "NIDOKING",
         "EEVEE": "VAPOREON"}


def read(p):
    return open(p, encoding="utf-8").read()


def write(p, s):
    open(p, "w", encoding="utf-8").write(s)


tp = read("src/data/trainer_parties.h")
if "FireRed QoL+Hard: post-game levels" in tp:
    sys.exit("Post-game levels are already scaled.")
tr = read("src/data/trainers.h")
party_of = dict(re.findall(r"\[(TRAINER_\w+)\] = \{.*?\.party = \w+\((sParty_\w+)\)", tr, re.S))

# Which trainers
src = "".join(read(f) for f in glob.glob("data/maps/*/scripts.inc") + ["data/scripts/trainers.inc"])
sevii = set()
for lab, body in re.findall(r"^(\w+)::\n(.*?)(?=^\w+::|\Z)", src, re.S | re.M):
    if lab.startswith(ISLANDS) and "TrainerTower" not in lab:
        sevii |= set(re.findall(r"trainerbattle\w*\s+(TRAINER_\w+)", body))
postgame = set()
for ids, mp in re.findall(r"\{ \{([^}]*)\},\s*MAP\((MAP_\w+)\) \}", read("src/vs_seeker.c")):
    ids = [x.strip() for x in ids.split(",")]
    if mp[4:].startswith(ISLAND_MAPS):
        sevii |= {t for t in ids if t != "SKIP"}
    else:
        postgame |= {t for t in ids[4:] if t != "SKIP"}
factor = {}
for t in postgame:
    if t in party_of:
        factor[party_of[t]] = POSTGAME_REMATCH
for t in sevii:
    if t in party_of:
        factor[party_of[t]] = SEVII_TRAINERS  # Sevii wins if a team is both

# Evolution rules
evo = read("src/data/pokemon/evolution.h")
level_evo = {}
for sp, body in re.findall(r"\[SPECIES_(\w+)\]\s*=\s*\{(.*?)\}\},", evo, re.S):
    for method, param, target in re.findall(r"\{?(EVO_LEVEL\w*),\s*(\d+),\s*SPECIES_(\w+)", body):
        if method != "EVO_LEVEL_SHEDINJA":
            level_evo.setdefault(sp, (int(param), target))


def evolve(sp, lvl):
    for _ in range(3):
        if sp in level_evo and level_evo[sp][0] <= lvl:
            sp = level_evo[sp][1]
        elif sp in STONE and lvl >= 45:
            sp = STONE[sp]
        else:
            break
    return sp


# Trainer parties
n_parties = 0
for party, f in factor.items():
    m = re.search(r"(static const struct \w+ %s\[\] = \{\n)(.*?)(\n\};\n)" % party, tp, re.S)
    if not m:
        continue
    body = m.group(2)
    team = re.findall(r"\.species = SPECIES_(\w+)", body)

    def bump(mon):
        lvl = min(100, round(int(re.search(r"\.lvl = (\d+)", mon).group(1)) * f))
        sp = re.search(r"\.species = SPECIES_(\w+)", mon).group(1)
        to = evolve(sp, lvl)
        if to != sp and to not in team:
            team[team.index(sp)] = to
            sp = to
        mon = re.sub(r"\.lvl = \d+", f".lvl = {lvl}", mon)
        return re.sub(r"\.species = SPECIES_\w+", f".species = SPECIES_{sp}", mon)

    body = re.sub(r"    \{\n.*?\n    \}", lambda x: bump(x.group(0)), body, flags=re.S)
    tp = tp[:m.start()] + "// FireRed QoL+Hard: post-game levels\n" + m.group(1) + body + m.group(3) + tp[m.end():]
    n_parties += 1
write("src/data/trainer_parties.h", tp)

# Wild Pokemon
raw = read("src/data/wild_encounters.json")
d = json.loads(raw)
n_slots = 0
for g in d["wild_encounter_groups"]:
    for e in g["encounters"]:
        if not e.get("map", "")[4:].startswith(ISLAND_MAPS):
            continue
        for key in e:
            if key.endswith("_mons") and "fishing" not in key:
                for mon in e[key]["mons"]:
                    mon["min_level"] = min(100, round(mon["min_level"] * SEVII_WILD))
                    mon["max_level"] = min(100, round(mon["max_level"] * SEVII_WILD))
                    n_slots += 1
write("src/data/wild_encounters.json", json.dumps(d, indent=2, ensure_ascii=False) + ("\n" if raw.endswith("\n") else ""))
print(f"{n_parties} trainer teams and {n_slots} wild slots scaled.")
