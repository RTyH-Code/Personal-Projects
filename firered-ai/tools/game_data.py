"""Extract what the playtester needs to know about a game from its pret source.

    python tools/game_data.py <pokefirered checkout> <profile name> > firered_ai/data/games/<name>.json

Run it on vanilla pret/pokefirered, or on a checkout with the FireRed QoL +
Hard patches applied (git am firered-qol-hard/source-patches/*.patch). It
reads the source as text and builds nothing. The profile holds:

- the save layout offsets that depend on the species count,
- species and Pokédex numbers, maps (with their region map section),
- trainers (name, where they're fought, highest level), level caps,
- the flags and vars the playtester checks, bag sizes, item ranges,
- the hack's release string, so a ROM can be recognised without its checksum.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

KNOWN_VANILLA = {"sb2_dex_owned": 0x28, "sb2_dex_seen": 0x5C, "sb2_encryption_key": 0xF20, "dex_flag_bytes": 52}



def species_entries(text):
    """(name, body) for each [SPECIES_X] = ... entry of a species table. Splits at each
    entry's own line, so a one-line entry ([SPECIES_NONE] = {0},) can't swallow the next."""
    parts = re.split(r"^\s*\[SPECIES_(\w+)\]\s*=", text, flags=re.M)
    return list(zip(parts[1::2], parts[2::2]))

def read(root, path):
    with open(os.path.join(root, path), encoding="utf-8") as f:
        return f.read()


def strip_comments(text):
    return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", text, flags=re.S))


class Consts:
    """#define and enum values from headers, with aliases and expressions resolved."""

    def __init__(self, root, headers):
        self.raw = {}
        for h in headers:
            text = strip_comments(read(root, h))
            for name, val in re.findall(r"^\s*#define\s+(\w+)[ \t]+([^\n]+)", text, re.M):
                self.raw.setdefault(name, val.strip())
            for body in re.findall(r"enum\s*\w*\s*\{(.*?)\}", text, re.S):
                i = -1
                for item in body.split(","):
                    item = item.strip()
                    if not item:
                        continue
                    if "=" in item:
                        name, val = (s.strip() for s in item.split("=", 1))
                        i = self.get(val) if not val.isdigit() else int(val)
                        self.raw.setdefault(name, str(i))
                    else:
                        i += 1
                        self.raw.setdefault(item, str(i))
        self.cache = {}

    def get(self, expr, depth=0):
        if isinstance(expr, int):
            return expr
        if expr in self.cache:
            return self.cache[expr]
        if depth > 40:
            raise ValueError(expr)
        val = self.raw.get(expr, expr)
        val = re.sub(r"\b[A-Za-z_]\w*\b",
                     lambda m: str(self.get(m.group(0), depth + 1)) if m.group(0) in self.raw else m.group(0), val)
        try:
            out = int(eval(val, {"__builtins__": {}}, {}))
        except Exception as e:
            raise ValueError(f"can't evaluate {expr} = {val}") from e
        if expr in self.raw:
            self.cache[expr] = out
        return out

    def names(self, prefix):
        out = {}
        for name in self.raw:
            if name.startswith(prefix):
                try:
                    out[name] = self.get(name)
                except ValueError:
                    pass
        return out


def save_layout(root, c):
    """Offsets of the Pokédex flags and encryption key, which move with NUM_SPECIES.

    Everything else the playtester reads is checked to sit where vanilla has it.
    """
    n = (c.get("NUM_SPECIES") + 7) // 8
    pokedex_size = (0x10 + 2 * n + 3) & ~3
    layout = {
        "dex_flag_bytes": n,
        "sb2_dex_owned": 0x18 + 0x10,
        "sb2_dex_seen": 0x18 + 0x10 + n,
        "sb2_encryption_key": 0xF20 + pokedex_size - 0x78,
    }
    # SaveBlock1: seen1[n] at 0x5F8 is followed by fields that end before
    # objectEvents (4-aligned at 0x6A0 in vanilla). Check the flags stay put.
    end = 0x5F8 + n
    end = (end + 1) & ~1  # u16 berryBlenderRecords
    end += 6 + 6 + 2  # berryBlenderRecords[3], unused_632[6], trainerRematchStepCounter
    end = (end + 1) & ~1  # ALIGNED(2) trainerRematches
    end += c.get("MAX_REMATCH_ENTRIES")
    object_events = (end + 3) & ~3
    if object_events != 0x6A0:
        raise SystemExit(f"SaveBlock1 layout moved (objectEvents at {object_events:#x}); update ram.py")
    g = strip_comments(read(root, "include/global.h"))
    sb2 = re.search(r"struct SaveBlock2\s*\{(.*?)encryptionKey", g, re.S).group(1)
    vanilla_fields = ["playerName", "playerGender", "specialSaveWarpFlags", "playerTrainerId", "playTimeHours",
                      "pokedex", "filler_90", "localTimeOffset", "lastBerryTreeUpdate", "battleTower", "mapView"]
    for f in vanilla_fields:
        if not re.search(rf"\b{f}\b", sb2):
            raise SystemExit(f"SaveBlock2 field {f} missing; update ram.py")
    counts = {k: c.get(k) for k in ["PC_ITEMS_COUNT", "BAG_ITEMS_COUNT", "BAG_KEYITEMS_COUNT",
                                    "BAG_POKEBALLS_COUNT", "BAG_TMHM_COUNT", "BAG_BERRIES_COUNT"]}
    off = 0x298 + 4 * counts["PC_ITEMS_COUNT"]
    pockets = {}
    for pocket, key in [("items", "BAG_ITEMS_COUNT"), ("key_items", "BAG_KEYITEMS_COUNT"),
                        ("poke_balls", "BAG_POKEBALLS_COUNT"), ("tm_hm", "BAG_TMHM_COUNT"),
                        ("berries", "BAG_BERRIES_COUNT")]:
        pockets[pocket] = [off, counts[key]]
        off += 4 * counts[key]
    if off != 0x5F8:
        raise SystemExit(f"bag pockets end at {off:#x}, not 0x5F8; update ram.py")
    layout["sb1_bag_pockets"] = pockets
    # The hack's Nuzlocke used-area bits. The offset comes from the source's
    # own offset comment (the playtester double-checks it while it plays).
    m = re.search(r"/\*(0x[0-9A-Fa-f]+)\*/\s*u8\s+hackNuzlockeAreas\[(\d+)\]", read(root, "include/global.h"))
    if m:
        layout["sb1_nuzlocke_areas"] = [int(m.group(1), 16), int(m.group(2))]
    return layout


def species_and_dex(root, c):
    species = {}
    for name, num in c.names("SPECIES_").items():
        if name in ("SPECIES_NONE", "SPECIES_EGG", "SPECIES_SHINY_TAG") or name.startswith(("SPECIES_OLD_UNOWN", "SPECIES_UNOWN_")):
            continue
        if not 0 < num < c.get("NUM_SPECIES"):
            continue
        species.setdefault(num, name.removeprefix("SPECIES_"))
    dex = {}
    for num, name in species.items():
        base = name
        while base and "NATIONAL_DEX_" + base not in c.raw and "_" in base:
            base = base.rsplit("_", 1)[0]  # a forme (DEOXYS_ATTACK) shares its species' entry
        if "NATIONAL_DEX_" + base in c.raw:
            dex[num] = c.get("NATIONAL_DEX_" + base)
    return species, dex


def map_sections(root):
    data = json.loads(read(root, "src/data/region_map/region_map_sections.json"))
    return [m["id"] for m in data["map_sections"]]


def maps(root):
    groups = json.loads(read(root, "data/maps/map_groups.json"))
    sections = map_sections(root)
    out = []
    for gi, g in enumerate(groups["group_order"]):
        for mi, name in enumerate(groups[g]):
            sec = None
            p = os.path.join(root, "data", "maps", name, "map.json")
            if os.path.exists(p):
                sec = json.load(open(p, encoding="utf-8")).get("region_map_section")
            out.append({"group": gi, "num": mi, "name": name, "section": sec,
                        "section_index": sections.index(sec) if sec in sections else None})
    return out


def parties(root):
    text = strip_comments(read(root, "src/data/trainer_parties.h"))
    out = {}
    for name, body in re.findall(r"static const struct \w+ (sParty_\w+)\[\]\s*=\s*\{(.*?)\n\};", text, re.S):
        out[name] = [int(x) for x in re.findall(r"\.lvl\s*=\s*(\d+)", body)]
    return out


def trainers(root, c):
    party_levels = parties(root)
    text = strip_comments(read(root, "src/data/trainers.h"))
    where = {}
    for path in glob.glob(os.path.join(root, "data", "maps", "*", "scripts.inc")):
        m = os.path.basename(os.path.dirname(path))
        for t in re.findall(r"trainerbattle\w*\s+(TRAINER_\w+)", open(path, encoding="utf-8").read()):
            where.setdefault(t, set()).add(m)
    out = {}
    for tid, body in re.findall(r"\[(TRAINER_\w+)\]\s*=\s*\{(.*?)\n    \},", text, re.S):
        try:
            num = c.get(tid)
        except ValueError:
            continue
        name = re.search(r'\.trainerName\s*=\s*_\("([^"]*)"\)', body)
        cls = re.search(r"\.trainerClass\s*=\s*TRAINER_CLASS_(\w+)", body)
        party = re.search(r"\.party\s*=\s*\w+\((sParty_\w+)\)", body)
        levels = party_levels.get(party.group(1), []) if party else []
        out[num] = {
            "id": tid.removeprefix("TRAINER_"),
            "name": name.group(1) if name else "",
            "class": cls.group(1) if cls else "",
            "max_level": max(levels) if levels else 0,
            "maps": sorted(where.get(tid, ())),
        }
    return out


def level_caps(root, c, trainer_info):
    code = strip_comments(read(root, "src/pokemon.c"))
    leaders = re.search(r"sHackCapLeaders\[\]\s*=\s*\{(.*?)\};", code, re.S)
    if not leaders:
        return None
    league = re.search(r"sHackCapLeague\[\]\s*=\s*\{(.*?)\};", code, re.S)
    level = lambda t: trainer_info[c.get(t)]["max_level"]  # noqa: E731
    return {
        "leaders": [level(t) for t in re.findall(r"TRAINER_\w+", leaders.group(1))],
        "league": max(level(t) for t in re.findall(r"TRAINER_\w+", league.group(1))),
    }


def battle_data(root, c):
    """Moves, species types and the type chart, so the playtester can pick good moves."""
    text = strip_comments(read(root, "src/data/battle_moves.h"))
    moves = {}
    for name, body in re.findall(r"\[MOVE_(\w+)\]\s*=\s*\{(.*?)\n    \},", text, re.S):
        try:
            num = c.get("MOVE_" + name)
        except ValueError:
            continue

        def field(f, default=0):
            m = re.search(rf"\.{f}\s*=\s*(\w+)", body)
            if not m:
                return default
            v = m.group(1)
            return int(v) if v.isdigit() else v

        moves[num] = {
            "name": name, "power": field("power"), "type": c.get(field("type", "TYPE_NORMAL")),
            "accuracy": field("accuracy"), "pp": field("pp"), "effect": str(field("effect", "")),
        }
    info = strip_comments(read(root, "src/data/pokemon/species_info.h"))
    types = {}
    for name, body in species_entries(info):
        m = re.search(r"\.types\s*=\s*\{\s*(\w+)\s*,\s*(\w+)\s*\}", body)
        if m:
            try:
                types[c.get("SPECIES_" + name)] = [c.get(m.group(1)), c.get(m.group(2))]
            except ValueError:
                pass
    code = strip_comments(read(root, "src/battle_main.c"))
    table = re.search(r"gTypeEffectiveness\[\w*\]\s*=\s*\{(.*?)\};", code, re.S).group(1)
    mul = {"TYPE_MUL_NO_EFFECT": 0, "TYPE_MUL_NOT_EFFECTIVE": 5, "TYPE_MUL_NORMAL": 10,
           "TYPE_MUL_SUPER_EFFECTIVE": 20}
    chart = []
    for a, d, m in re.findall(r"(TYPE_\w+)\s*,\s*(TYPE_\w+)\s*,\s*(TYPE_MUL_\w+)", table):
        if "FORESIGHT" in a or "ENDTABLE" in a:
            continue  # markers in the table, not types (the Ghost immunities after them still apply)
        chart.append([c.get(a), c.get(d), mul[m]])
    return {"moves": {str(k): v for k, v in sorted(moves.items())},
            "species_types": {str(k): v for k, v in sorted(types.items())},
            "type_chart": chart}


GYM_LEADERS = ["LEADER_BROCK", "LEADER_MISTY", "LEADER_LT_SURGE", "LEADER_ERIKA", "LEADER_KOGA",
               "LEADER_SABRINA", "LEADER_BLAINE", "LEADER_GIOVANNI"]
LEAGUE = ["ELITE_FOUR_LORELEI", "ELITE_FOUR_BRUNO", "ELITE_FOUR_AGATHA", "ELITE_FOUR_LANCE",
          "CHAMPION_FIRST_SQUIRTLE", "CHAMPION_FIRST_BULBASAUR", "CHAMPION_FIRST_CHARMANDER"]


def gym_levels(trainer_info):
    """Each Gym Leader's highest level, then the Elite Four's and Champion's."""
    by_id = {t["id"]: t for t in trainer_info.values()}
    return {"leaders": [by_id[n]["max_level"] for n in GYM_LEADERS if n in by_id],
            "league": max((by_id[n]["max_level"] for n in LEAGUE if n in by_id), default=0)}


def encode(root, text):
    table = {}
    for line in read(root, "charmap.txt").splitlines():
        m = re.match(r"^'(.)'\s*=\s*([0-9A-Fa-f]{2})\s*$", line)
        if m:
            table.setdefault(m.group(1), int(m.group(2), 16))
    table[" "] = 0x00
    return [table[ch] for ch in text]


def release_info(root):
    """The 'QoL+HARD R14' string the Options screen shows, encoded as in the ROM."""
    p = os.path.join(root, "include", "hack_version.h")
    if not os.path.exists(p):
        return None
    release = re.search(r'HACK_RELEASE_STRING\s+"([^"]+)"', open(p).read()).group(1)
    prefix = "QoL+HARD "
    return {"release": release, "signature": encode(root, prefix), "release_chars": encode(root, "R0123456789")}


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    root, name = sys.argv[1], sys.argv[2]
    c = Consts(root, ["include/constants/species.h", "include/constants/pokedex.h", "include/constants/flags.h",
                      "include/constants/vars.h", "include/constants/opponents.h", "include/constants/items.h",
                      "include/constants/global.h", "include/constants/pokemon.h", "include/global.h",
                      "include/constants/battle.h", "include/constants/moves.h", "include/constants/vars.h"])
    species, dex = species_and_dex(root, c)
    trainer_info = trainers(root, c)
    flags = {k.removeprefix("FLAG_"): v for k, v in c.names("FLAG_").items() if 0 <= v < 0x900}
    story_vars = {k.removeprefix("VAR_"): v for k, v in c.names("VAR_").items() if 0x4000 <= v < 0x4100}
    profile = {
        "name": name,
        "release": release_info(root),
        "layout": save_layout(root, c),
        "num_species": c.get("NUM_SPECIES"),
        "dex_count": c.get("NATIONAL_DEX_COUNT"),
        "species": {str(k): v for k, v in sorted(species.items())},
        "species_dex": {str(k): v for k, v in sorted(dex.items())},
        "maps": maps(root),
        "trainer_flags_start": c.get("TRAINER_FLAGS_START"),
        "trainers": {str(k): v for k, v in sorted(trainer_info.items())},
        "level_caps": level_caps(root, c, trainer_info),
        "flags": dict(sorted(flags.items(), key=lambda kv: kv[1])),
        "vars": dict(sorted(story_vars.items(), key=lambda kv: kv[1])),
        "items_count": c.get("ITEMS_COUNT"),
        "poke_balls": [c.get("ITEM_MASTER_BALL"), c.get("ITEM_PREMIER_BALL")],
        "max_level": 100,
        "kanto_mapsec_start": map_sections(root).index("MAPSEC_PALLET_TOWN"),
        "battle_types": {k.removeprefix("BATTLE_TYPE_"): v for k, v in c.names("BATTLE_TYPE_").items() if v < 1 << 31},
        "shiny_odds": c.get("SHINY_ODDS"),
        "gym_levels": gym_levels(trainer_info),
        "items": {k.removeprefix("ITEM_"): v for k, v in sorted(c.names("ITEM_").items(), key=lambda kv: kv[1])
                  if 0 < v < c.get("ITEMS_COUNT")},
        **battle_data(root, c),
    }
    if name == "firered":
        for k, v in KNOWN_VANILLA.items():
            assert profile["layout"][k] == v, (k, profile["layout"][k], v)
    json.dump(profile, sys.stdout, indent=1)
    print()
    print(f"{name}: {len(species)} species (dex up to {profile['dex_count']}), {len(profile['maps'])} maps, "
          f"{len(trainer_info)} trainers, release {profile['release']['release'] if profile['release'] else '-'}, "
          f"level caps {profile['level_caps']}", file=sys.stderr)


if __name__ == "__main__":
    main()
