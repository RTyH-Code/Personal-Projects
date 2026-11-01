#!/usr/bin/env python3
"""Wild encounter pass: make every non-legendary Pokemon obtainable in FireRed.

Each placement overwrites one slot of an existing FireRed encounter table. Only
slots whose species also appears in another slot of the same table are used, so
nothing that was already there disappears. Afterwards the script re-checks that
all 386 species can be obtained (wild, gift, static, evolution or breeding).

Run from the repo root on a checkout without these changes applied:
    python3 tools/hack/encounters.py
"""
import json
import re
import sys

WILD = "src/data/wild_encounters.json"

# Preferred slot order per table kind (index into the mons list).
#   land  rates: 20 20 10 10 10 10 5 5 4 4 1 1
#   water/rock : 60 30 5 4 1
#   fishing    : old 70 30 | good 60 20 20 | super 40 40 15 4 1
PREF = {
    "land": [6, 7, 8, 9, 4, 5, 2, 3, 10, 11],
    "water": [2, 3, 1, 4],
    "rock": [2, 3, 1, 4],
    "good": [3, 4],
    "super": [7, 8, 6, 9, 5],
}
RATES = {
    "land": [20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1],
    "water": [60, 30, 5, 4, 1],
    "rock": [60, 30, 5, 4, 1],
    "good": [70, 30, 60, 20, 20, 40, 40, 15, 4, 1],
    "super": [70, 30, 60, 20, 20, 40, 40, 15, 4, 1],
}
RATE_PREF = {
    "land": [5, 4, 10, 1, 20],
    "water": [5, 4, 30, 1, 60],
    "rock": [5, 4, 30, 1, 60],
    "good": [20, 60],
    "super": [15, 4, 40, 1],
}
ORIG_TOTAL = {}
KIND_KEY = {"land": "land_mons", "water": "water_mons", "rock": "rock_smash_mons",
            "good": "fishing_mons", "super": "fishing_mons"}

# (map, table, species, levels or None to keep the slot's levels)
PLACEMENTS = [
    # --- Kanto starters
    ("ROUTE25", "land", "BULBASAUR", (10, 14)),
    ("ROUTE4", "land", "CHARMANDER", (8, 12)),
    ("ROUTE24", "land", "SQUIRTLE", (10, 14)),
    # --- Early routes: common Hoenn critters
    ("ROUTE1", "land", "ZIGZAGOON", None),
    ("ROUTE1", "land", "TAILLOW", None),
    ("ROUTE2", "land", "WURMPLE", None),
    ("ROUTE2", "land", "RALTS", None),
    ("VIRIDIAN_FOREST", "land", "SEEDOT", None),
    ("VIRIDIAN_FOREST", "land", "SHROOMISH", None),
    ("ROUTE3", "land", "POOCHYENA", None),
    ("ROUTE3", "land", "SKITTY", None),
    ("MT_MOON_1F", "land", "ARON", None),
    ("MT_MOON_B2F", "land", "LUNATONE", None),
    ("MT_MOON_B2F", "land", "SOLROCK", None),
    ("ROUTE4", "land", "SANDSHREW", None),
    ("ROUTE24", "land", "BELLSPROUT", None),
    ("ROUTE25", "land", "BELLSPROUT", None),
    ("ROUTE24", "land", "NINCADA", None),
    ("ROUTE22", "water", "SURSKIT", None),
    ("ROUTE6", "water", "LOTAD", None),
    ("ROUTE5", "land", "SNUBBULL", None),
    ("ROUTE6", "land", "MARILL", None),
    ("ROUTE9", "land", "CACNEA", None),
    ("VIRIDIAN_FOREST", "land", "SLAKOTH", None),
    ("ROUTE6", "land", "SNUBBULL", None),
    ("ROUTE7", "land", "VULPIX", None),
    ("ROUTE8", "land", "VULPIX", None),
    ("ROUTE8", "land", "SANDSHREW", None),
    ("ROUTE8", "land", "GULPIN", None),
    ("ROUTE10", "land", "ELECTRIKE", None),
    ("ROUTE11", "land", "SPOINK", None),
    ("DIGLETTS_CAVE_B1F", "land", "TRAPINCH", None),
    ("DIGLETTS_CAVE_B1F", "land", "WHISMUR", None),
    ("ROCK_TUNNEL_1F", "land", "MAKUHITA", None),
    ("ROCK_TUNNEL_1F", "land", "ARON", None),
    ("ROCK_TUNNEL_B1F", "land", "MAWILE", None),
    ("ROCK_TUNNEL_B1F", "rock", "NOSEPASS", None),
    ("POKEMON_TOWER_3F", "land", "SHUPPET", None),
    ("POKEMON_TOWER_4F", "land", "DUSKULL", None),
    ("POKEMON_TOWER_5F", "land", "MISDREAVUS", None),
    ("POKEMON_TOWER_6F", "land", "SHUPPET", None),
    ("POKEMON_TOWER_6F", "land", "DUSKULL", None),
    ("POKEMON_TOWER_7F", "land", "MISDREAVUS", None),
    ("POKEMON_TOWER_7F", "land", "CHIMECHO", None),
    ("ROUTE12", "land", "HOOTHOOT", None),
    ("ROUTE12", "water", "SLOWPOKE", None),
    ("ROUTE13", "land", "HOOTHOOT", None),
    ("ROUTE14", "land", "ROSELIA", None),
    ("ROUTE14", "land", "CASTFORM", None),
    ("ROUTE15", "land", "SUNKERN", None),
    ("ROUTE15", "land", "VOLBEAT", None),
    ("ROUTE15", "land", "ILLUMISE", None),
    ("ROUTE16", "land", "SPINDA", None),
    ("ROUTE16", "land", "KECLEON", None),
    ("ROUTE17", "land", "ZANGOOSE", None),
    ("ROUTE17", "land", "SEVIPER", None),
    ("ROUTE18", "land", "WINGULL", None),
    ("POWER_PLANT", "land", "ELECTRIKE", None),
    ("POWER_PLANT", "land", "PLUSLE", None),
    ("POWER_PLANT", "land", "MINUN", None),
    ("POKEMON_MANSION_1F", "land", "VULPIX", None),
    ("POKEMON_MANSION_B1F", "land", "MAGMAR", None),
    ("SEAFOAM_ISLANDS_1F", "land", "SLOWPOKE", None),
    ("SEAFOAM_ISLANDS_B1F", "land", "SNORUNT", None),
    ("SEAFOAM_ISLANDS_B2F", "land", "SNORUNT", None),
    ("SEAFOAM_ISLANDS_B3F", "land", "SPHEAL", None),
    # --- Safari Zone
    ("SAFARI_ZONE_CENTER", "land", "PINSIR", None),
    ("SAFARI_ZONE_EAST", "land", "PINSIR", None),
    ("SAFARI_ZONE_EAST", "land", "GIRAFARIG", None),
    ("SAFARI_ZONE_NORTH", "land", "GIRAFARIG", None),
    ("SAFARI_ZONE_WEST", "land", "KECLEON", None),
    ("SAFARI_ZONE_CENTER", "super", "BARBOACH", None),
    ("SAFARI_ZONE_WEST", "super", "CORPHISH", None),
    ("SAFARI_ZONE_NORTH", "super", "FEEBAS", None),
    # --- Sea routes
    ("ROUTE19", "water", "WINGULL", None),
    ("ROUTE19", "water", "MANTINE", None),
    ("ROUTE19", "super", "CARVANHA", None),
    ("ROUTE19", "super", "CHINCHOU", None),
    ("ROUTE20", "water", "WAILMER", None),
    ("ROUTE20", "water", "CORSOLA", None),
    ("ROUTE20", "good", "LUVDISC", None),
    ("ROUTE20", "super", "CLAMPERL", None),
    ("ROUTE21_NORTH", "super", "STARYU", None),
    ("ROUTE21_SOUTH", "super", "REMORAID", None),
    ("ROUTE21_SOUTH", "super", "STARYU", None),
    ("CINNABAR_ISLAND", "super", "STARYU", None),
    ("VERMILION_CITY", "super", "REMORAID", None),
    ("ROUTE12", "super", "BARBOACH", None),
    # --- Victory Road
    ("VICTORY_ROAD_1F", "land", "MEDITITE", None),
    ("VICTORY_ROAD_2F", "land", "BAGON", (25, 29)),
    ("VICTORY_ROAD_3F", "land", "BELDUM", (25, 29)),
    # --- Sevii Islands 1-3 (mid-game)
    ("ONE_ISLAND_KINDLE_ROAD", "land", "CYNDAQUIL", (15, 18)),
    ("ONE_ISLAND_KINDLE_ROAD", "land", "NUMEL", None),
    ("ONE_ISLAND_TREASURE_BEACH", "land", "WINGULL", None),
    ("ONE_ISLAND_TREASURE_BEACH", "water", "CORSOLA", None),
    ("ONE_ISLAND_TREASURE_BEACH", "good", "LUVDISC", None),
    ("TWO_ISLAND_CAPE_BRINK", "land", "TOTODILE", (15, 18)),
    ("TWO_ISLAND_CAPE_BRINK", "water", "LOTAD", None),
    ("THREE_ISLAND_BERRY_FOREST", "land", "SUDOWOODO", None),
    ("THREE_ISLAND_BERRY_FOREST", "land", "SUNKERN", None),
    ("THREE_ISLAND_BOND_BRIDGE", "water", "WAILMER", None),
    ("MT_EMBER_EXTERIOR", "land", "TORCHIC", (15, 18)),
    ("MT_EMBER_EXTERIOR", "land", "NUMEL", None),
    ("MT_EMBER_RUBY_PATH_1F", "land", "MAGMAR", None),
    ("MT_EMBER_RUBY_PATH_B1F", "land", "TORKOAL", None),
    # --- Sevii Islands 4-7 (post-game)
    ("FOUR_ISLAND_ICEFALL_CAVE_1F", "land", "SNEASEL", None),
    ("FOUR_ISLAND_ICEFALL_CAVE_1F", "land", "SNORUNT", None),
    ("FOUR_ISLAND_ICEFALL_CAVE_B1F", "land", "SPHEAL", None),
    ("FOUR_ISLAND_ICEFALL_CAVE_B1F", "land", "SNEASEL", None),
    ("FIVE_ISLAND_MEADOW", "land", "CHIKORITA", (15, 18)),
    ("FIVE_ISLAND_MEADOW", "land", "MILTANK", None),
    ("FIVE_ISLAND_MEADOW", "land", "TROPIUS", None),
    ("FIVE_ISLAND_MEMORIAL_PILLAR", "land", "SWABLU", None),
    ("FIVE_ISLAND_WATER_LABYRINTH", "super", "FEEBAS", None),
    ("FIVE_ISLAND_RESORT_GORGEOUS", "water", "MANTINE", None),
    ("FIVE_ISLAND_LOST_CAVE_ROOM1", "land", "SABLEYE", None),
    ("FIVE_ISLAND_LOST_CAVE_ROOM5", "land", "SABLEYE", None),
    ("FIVE_ISLAND_LOST_CAVE_ROOM10", "land", "DUSKULL", None),
    ("SIX_ISLAND_PATTERN_BUSH", "land", "TREECKO", (15, 18)),
    ("SIX_ISLAND_RUIN_VALLEY", "land", "MUDKIP", (15, 18)),
    ("SIX_ISLAND_RUIN_VALLEY", "land", "BALTOY", None),
    ("SIX_ISLAND_WATER_PATH", "super", "CHINCHOU", None),
    ("SIX_ISLAND_OUTCAST_ISLAND", "super", "CLAMPERL", None),
    ("SEVEN_ISLAND_SEVAULT_CANYON_ENTRANCE", "land", "ABSOL", None),
    ("ROUTE23", "land", "GLIGAR", None),
    ("SEVEN_ISLAND_SEVAULT_CANYON", "rock", "LILEEP", None),
    ("SEVEN_ISLAND_SEVAULT_CANYON", "rock", "ANORITH", None),
    ("SEVEN_ISLAND_TANOBY_RUINS", "super", "RELICANTH", None),
]

# The first Altering Cave table is the only one used without Mystery Gift.
# Turn it into a mixed cave holding all of the Mystery Gift species.
ALTERING_CAVE = [  # slot: (species, min, max)
    (2, "MAREEP", 18, 22), (3, "PINECO", 20, 24), (4, "HOUNDOUR", 20, 24),
    (5, "TEDDIURSA", 20, 24), (6, "AIPOM", 20, 24), (7, "SHUCKLE", 20, 24),
    (8, "STANTLER", 20, 24), (9, "SMEARGLE", 20, 24),
]

# Obtainable outside the wild/scripted-gift scan below.
EXTRA_SOURCES = [
    "HITMONLEE",    # Fighting Dojo (species held in a variable)
    "PORYGON",      # Game Corner (species held in a variable)
]
# Placed as one-time legendary encounters by tools/hack/legendaries.py
LEGENDARY_EVENTS = [
    "MEW", "CELEBI", "RAIKOU", "ENTEI", "SUICUNE", "LUGIA", "HO_OH", "DEOXYS",
    "REGIROCK", "REGICE", "REGISTEEL", "KYOGRE", "GROUDON", "RAYQUAZA",
    "LATIAS", "LATIOS", "JIRACHI",
]


def fr_tables(data):
    """Map name -> FireRed encounter entry (first one only, see Altering Cave)."""
    out = {}
    for e in data["wild_encounter_groups"][0]["encounters"]:
        if e["base_label"].endswith("FireRed") and e["map"] not in out:
            out[e["map"]] = e
    return out


def mons_for(entry, kind):
    mons = entry[KIND_KEY[kind]]["mons"]
    if kind == "good":
        return mons, range(2, 5)
    if kind == "super":
        return mons, range(5, 10)
    if kind in ("water", "rock"):
        return mons, range(0, 5)
    return mons, range(0, 12)


FALLBACK = {"super": ["super", "good"], "good": ["good", "super"]}


def place(tables, used, mapname, kind, species, levels):
    for k in FALLBACK.get(kind, [kind]):
        if try_place(tables, used, mapname, k, species, levels):
            return True
    print(f"no free slot for {species} in {mapname} {kind}")
    return False


def try_place(tables, used, mapname, kind, species, levels):
    entry = tables["MAP_" + mapname]
    mons, allowed = mons_for(entry, kind)
    # A slot may be replaced if its species still appears elsewhere on this map.
    counts = {}
    for k in set(KIND_KEY.values()):
        for m in entry.get(k, {}).get("mons", []):
            counts[m["species"]] = counts.get(m["species"], 0) + 1
    rates = RATES[kind]
    total = {}
    for i in allowed:
        total[mons[i]["species"]] = total.get(mons[i]["species"], 0) + rates[i]
    free = [slot for slot in PREF[kind]
            if slot in allowed and (mapname, kind, slot) not in used
            and counts[mons[slot]["species"]] >= 2]
    # Only common species (>= 20% of the table) give up slots, and never more
    # than half of their original share; otherwise fall back to any duplicate.
    candidates = [i for i in free
                  if total[mons[i]["species"]] >= 20
                  and total[mons[i]["species"]] - rates[i] >= ORIG_TOTAL.setdefault((mapname, kind, mons[i]["species"]), total[mons[i]["species"]]) / 2]
    if not candidates:
        candidates = free
    if not candidates:
        return False
    # Prefer slots with ~5% odds, and among those take from the most common
    # species so rarer ones keep their odds.
    slot = min(candidates, key=lambda i: (RATE_PREF[kind].index(rates[i]), -total[mons[i]["species"]]))
    mons[slot]["species"] = "SPECIES_" + species
    if levels:
        mons[slot]["min_level"], mons[slot]["max_level"] = levels
    used.add((mapname, kind, slot))
    return True


def obtainable(data):
    species = [k for k in re.findall(r"#define (SPECIES_\w+)\s+\d+", open("include/constants/species.h").read())
               if not k.startswith(("SPECIES_OLD_UNOWN", "SPECIES_UNOWN_")) and k not in ("SPECIES_NONE", "SPECIES_EGG")]
    ok = {"SPECIES_" + s for s in EXTRA_SOURCES + LEGENDARY_EVENTS}
    for e in fr_tables(data).values():
        for k in KIND_KEY.values():
            for m in e.get(k, {}).get("mons", []):
                ok.add(m["species"])
    import glob
    for f in glob.glob("data/**/*.inc", recursive=True):
        for sp in re.findall(r"(?:givemon|setwildbattle|giveegg)\s+(SPECIES_\w+)", open(f).read()):
            ok.add(sp)
    ok.update(re.findall(r"\.species = (SPECIES_\w+)", open("src/data/ingame_trades.h").read()))
    evo, pre = {}, {}
    for a, body in re.findall(r"\[(SPECIES_\w+)\]\s*=\s*\{(.*?)\}\},", open("src/data/pokemon/evolution.h").read(), re.S):
        evo[a] = re.findall(r"SPECIES_\w+", body)
        for t in evo[a]:
            pre[t] = a
    changed = True
    while changed:
        changed = False
        for a in list(ok):
            for t in evo.get(a, []) + ([pre[a]] if a in pre else []):
                if t not in ok:
                    ok.add(t)
                    changed = True
    return [s for s in species if s not in ok]


def main():
    data = json.load(open(WILD))
    tables = fr_tables(data)
    used = set()
    ok = [place(tables, used, *p) for p in PLACEMENTS]
    if not all(ok):
        sys.exit("some placements failed")
    cave = tables["MAP_SIX_ISLAND_ALTERING_CAVE"]["land_mons"]["mons"]
    for slot, species, lo, hi in ALTERING_CAVE:
        cave[slot] = {"min_level": lo, "max_level": hi, "species": "SPECIES_" + species}
    missing = obtainable(data)
    if missing:
        sys.exit("still unobtainable: " + " ".join(missing))
    with open(WILD, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"{len(PLACEMENTS)} placements + Altering Cave applied; all species obtainable")


if __name__ == "__main__":
    main()
