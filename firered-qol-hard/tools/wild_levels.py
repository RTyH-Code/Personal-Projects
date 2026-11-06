#!/usr/bin/env python3
"""Scale wild Pokemon levels by 1.15x, like the trainers, from the Erika stretch on.

Covers the story areas from Routes 7-10 and Rock Tunnel through the Sevii
Islands 1-3. Route 23, Victory Road and Cerulean Cave were scaled earlier
(release 10); the post-game Sevii Islands 4-7 are left alone. Runs once.
"""
import json, os, sys

os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FACTOR = 1.15
MAPS = ("ROUTE7", "ROUTE8", "ROUTE9", "ROUTE10", "ROUTE11", "ROUTE12", "ROUTE13", "ROUTE14", "ROUTE15", "ROUTE16",
        "ROUTE17", "ROUTE18", "ROUTE19", "ROUTE20", "ROUTE21_NORTH", "ROUTE21_SOUTH", "ROCK_TUNNEL", "POKEMON_TOWER",
        "SAFARI_ZONE", "POWER_PLANT", "SEAFOAM_ISLANDS", "POKEMON_MANSION", "ONE_ISLAND", "TWO_ISLAND", "THREE_ISLAND",
        "MT_EMBER")
P = "src/data/wild_encounters.json"
raw = open(P, encoding="utf-8").read()
if '"_hack_wild_levels_scaled": true' in raw:
    sys.exit("Wild levels are already scaled.")
d = json.loads(raw)
n = 0
for g in d["wild_encounter_groups"]:
    for e in g["encounters"]:
        m = e.get("map", "")[4:]
        if not any(m == k or m.startswith(k + "_") for k in MAPS):
            continue
        for key in e:
            if not key.endswith("_mons") or "fishing" in key:
                continue  # rod levels stay as they are (an Old Rod is always Lv. 5)
            for mon in e[key]["mons"]:
                mon["min_level"] = min(100, round(mon["min_level"] * FACTOR))
                mon["max_level"] = min(100, round(mon["max_level"] * FACTOR))
                n += 1
d["_hack_wild_levels_scaled"] = True
open(P, "w", encoding="utf-8").write(json.dumps(d, indent=2, ensure_ascii=False) + ("\n" if raw.endswith("\n") else ""))
print(f"{n} encounter slots scaled by {FACTOR}.")
