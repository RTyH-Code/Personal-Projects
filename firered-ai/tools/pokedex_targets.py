"""Work out which Pokémon one FireRed save can own, from pret/pokefirered source.

    python tools/pokedex_targets.py <pokefirered checkout> <game name> > out.json

It reads the game's data as text (nothing is built or run) and follows
every way to get a Pokémon without trading or Mystery Gift:
- wild encounters (FireRed tables; Altering Cave's first table only),
- gifts, static and legendary encounters and eggs given by scripts (incl. Game Corner
  prizes and other species chosen through a variable),
- in-game trades,
- the roaming legendary,
- evolution, but only by methods that work in this game: no trade
  evolutions, no day/night evolutions if the clock code is disabled
  (it is in FRLG), no Beauty evolution (FRLG has no Pokéblocks), and
  stone evolutions only if the stone can be found or bought,
- breeding at the Day Care (with Ditto), including incense babies when
  the incense can be found.

Some choices lock others out for the rest of the save: the starter (which
also decides the roaming legendary) and, in vanilla, the Mt. Moon fossil. These come out
as "choices": the Pokédex counts as complete when one option of each is.

The Navel Rock and Birth Island legendaries count only if some script gives
the ticket to reach them.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

VERSION_DEFINES = {"FIRERED"}
STARTER_MAP = "PalletTown_ProfessorOaksLab"
FOSSIL_MAP = "CinnabarIsland_PokemonLab_ExperimentRoom"
FOSSIL_CHOICE = ["OMANYTE", "KABUTO"]  # Mt. Moon fossils (the Old Amber is separate)
EVENT_ISLANDS = {"NavelRock": "MYSTIC_TICKET", "BirthIsland": "AURORA_TICKET"}
ALWAYS_OK = {
    "EVO_FRIENDSHIP", "EVO_LEVEL", "EVO_LEVEL_ATK_GT_DEF", "EVO_LEVEL_ATK_EQ_DEF",
    "EVO_LEVEL_ATK_LT_DEF", "EVO_LEVEL_SILCOON", "EVO_LEVEL_CASCOON",
    "EVO_LEVEL_NINJASK", "EVO_LEVEL_SHEDINJA",
}
NEVER_OK = {"EVO_TRADE", "EVO_TRADE_ITEM", "EVO_BEAUTY"}
INCENSE_BABIES = {"WYNAUT": ("WOBBUFFET", "LAX_INCENSE"), "AZURILL": ("MARILL", "SEA_INCENSE")}
CHECK_ONLY = re.compile(r"\b(checkitem|removeitem|checkitemspace|checkitemtype|checkpcitem)\b")


def read(root, path):
    with open(os.path.join(root, path), encoding="utf-8") as f:
        return f.read()


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def preprocess(text):
    """Keep only FireRed's side of `.ifdef FIRERED / LEAFGREEN` blocks."""
    out, stack = [], []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(".ifdef ") or s.startswith(".ifndef "):
            name = s.split()[1]
            on = (name in VERSION_DEFINES) == s.startswith(".ifdef ")
            stack.append(on)
        elif s == ".else" and stack:
            stack[-1] = not stack[-1]
        elif s == ".endif" and stack:
            stack.pop()
        elif all(stack):
            out.append(line)
    return "\n".join(out)


def species_tables(root):
    species = {}
    for name, num in re.findall(r"#define SPECIES_(\w+) (\d+)", read(root, "include/constants/species.h")):
        if name in ("NONE", "EGG") or name.startswith(("OLD_UNOWN", "UNOWN_")):
            continue
        species[name] = int(num)
    body = read(root, "include/constants/pokedex.h")
    body = body[body.index("NATIONAL_DEX_NONE"):]
    dex = {}
    for i, name in enumerate(re.findall(r"NATIONAL_DEX_(\w+),", body)):
        if name != "NONE":
            dex[name] = i
    return {s: dex[s] for s in species if s in dex}


def evolutions(root):
    text = strip_comments(read(root, "src/data/pokemon/evolution.h"))
    evo = {}
    for src, body in re.findall(r"\[SPECIES_(\w+)\]\s*=\s*\{(.*?)\}\},", text, re.S):
        evo[src] = re.findall(r"\{\s*(EVO_\w+)\s*,\s*(\w+)\s*,\s*SPECIES_(\w+)\s*\}", body + "}")
    return evo


def working_evo_methods(root):
    """EVO_ methods whose case in GetEvolutionTargetSpecies can succeed."""
    code = strip_comments(read(root, "src/pokemon.c"))
    ok = set(ALWAYS_OK) | {"EVO_ITEM"}
    for method in ("EVO_FRIENDSHIP_DAY", "EVO_FRIENDSHIP_NIGHT"):
        m = re.search(rf"case {method}:(.*?)break;", code, re.S)
        if m and "targetSpecies =" in m.group(1):
            ok.add(method)
    return ok - NEVER_OK


def egg_groups(root):
    text = read(root, "src/data/pokemon/species_info.h")
    out = {}
    for name, body in re.findall(r"\[SPECIES_(\w+)\]\s*=\s*(.*?)\n    \},?", text, re.S):
        m = re.search(r"\.eggGroups = \{\s*(\w+)\s*,\s*(\w+)\s*\}", body)
        if m:
            out[name] = {m.group(1), m.group(2)}
        elif "SPECIES_INFO_UNDISCOVERED" in body or "OLD_UNOWN" in body:
            out[name] = {"EGG_GROUP_UNDISCOVERED"}
    return out


def script_files(root):
    files = sorted(glob.glob(os.path.join(root, "data", "**", "*.inc"), recursive=True))
    return {os.path.relpath(f, root): preprocess(open(f, encoding="utf-8").read()) for f in files}


def map_of(path):
    parts = path.split(os.sep)
    return parts[2] if len(parts) > 3 and parts[1] == "maps" else None


def obtainable_items(root, scripts, open_islands):
    items = set()
    sources = dict(scripts)
    for f in glob.glob(os.path.join(root, "data", "maps", "*", "map.json")):
        sources[os.path.relpath(f, root)] = open(f, encoding="utf-8").read()
    for path, text in sources.items():
        m = map_of(path)
        if m and any(m.startswith(i) for i in EVENT_ISLANDS if i not in open_islands):
            continue
        for line in text.splitlines():
            if not CHECK_ONLY.search(line):
                items.update(re.findall(r"\bITEM_(\w+)", line))
    return items


def mt_moon_fossils_exclusive(scripts):
    """In vanilla, taking one Mt. Moon fossil also removes the other one.

    Each fossil object is then removed twice in the script (once when you take
    it, once when you take the other); if it's removed only once, you can
    take both.
    """
    text = scripts.get(os.path.join("data", "maps", "MtMoon_B2F", "scripts.inc"), "")
    counts = [len(re.findall(rf"removeobject\s+LOCALID_{f}_FOSSIL\b", text)) for f in ("HELIX", "DOME")]
    return max(counts) > 1


def analyse(root):
    dex = species_tables(root)
    evo = evolutions(root)
    methods = working_evo_methods(root)
    eggs = egg_groups(root)
    scripts = script_files(root)

    # Which event islands can be reached: some script outside them gives the ticket.
    open_islands = set()
    for island, ticket in EVENT_ISLANDS.items():
        for path, text in scripts.items():
            if (map_of(path) or "").startswith(island):
                continue
            if re.search(rf"\b(additem|giveitem|giveitem_msg)\s+ITEM_{ticket}\b", text):
                open_islands.add(island)
    items = obtainable_items(root, scripts, open_islands)

    seeds, choice_seeds = set(), {}
    for path, text in scripts.items():
        m = map_of(path)
        if m and any(m.startswith(i) for i in EVENT_ISLANDS if i not in open_islands):
            continue
        found = set(re.findall(r"\b(?:givemon|setwildbattle|seteventmon|giveegg)\s+SPECIES_(\w+)", text))
        if re.search(r"\bgivemon\s+VAR_\w+", text) or re.search(r"\bgivemon\s+PLAYER_STARTER_SPECIES", text):
            found |= set(re.findall(r"\bsetvar\s+\w+\s*,\s*SPECIES_(\w+)", text))
        if m == STARTER_MAP:
            choice_seeds.setdefault("starter", set()).update(found)
            continue
        if m == FOSSIL_MAP and mt_moon_fossils_exclusive(scripts):
            choice_seeds.setdefault("fossil", set()).update(found & set(FOSSIL_CHOICE))
            found -= set(FOSSIL_CHOICE)
        seeds |= found

    wild = json.loads(read(root, "src/data/wild_encounters.json"))
    seen_maps = set()
    for e in wild["wild_encounter_groups"][0]["encounters"]:
        if not e["base_label"].endswith("FireRed") or e["map"] in seen_maps:
            continue
        seen_maps.add(e["map"])
        for k, v in e.items():
            if isinstance(v, dict) and "mons" in v:
                seeds |= {mon["species"].removeprefix("SPECIES_") for mon in v["mons"]}
    seeds |= set(re.findall(r"\.species = SPECIES_(\w+)", read(root, "src/data/ingame_trades.h")))

    # Roamer: decided by the starter.
    roamer = {}
    rc = read(root, "src/roamer.c")
    m = re.search(r"GetRoamerSpecies\(\).*?\}\)", rc, re.S)
    if m and "InitRoamer" in "".join(scripts.values()):
        default = re.search(r"default:\\?\s*a = SPECIES_(\w+)", m.group(0)).group(1)
        for starter, mon in re.findall(r"case SPECIES_(\w+):\\?\s*a = SPECIES_(\w+)", m.group(0)):
            roamer[starter] = mon
        roamer["*"] = default

    pre = {}
    for a, targets in evo.items():
        for _, _, t in targets:
            pre[t] = a

    def can_evolve(method, param):
        if method == "EVO_ITEM":
            return param.removeprefix("ITEM_") in items
        return method in methods

    def egg_species(s):
        while s in pre:
            s = pre[s]
        if s in INCENSE_BABIES and INCENSE_BABIES[s][1] not in items:
            s = INCENSE_BABIES[s][0]
        return s

    has_ditto = lambda ok: "DITTO" in ok  # noqa: E731

    def closure(start):
        ok = set(start) & set(dex)
        changed = True
        while changed:
            changed = False
            for s in list(ok):
                nxt = [t for method, param, t in evo.get(s, []) if can_evolve(method, param)]
                if has_ditto(ok) and s != "DITTO" and "EGG_GROUP_UNDISCOVERED" not in eggs.get(s, set()):
                    nxt.append(egg_species(s))
                for t in nxt:
                    if t not in ok and t in dex:
                        ok.add(t)
                        changed = True
        return ok

    base = closure(seeds)
    choices = []
    starters = sorted(choice_seeds.get("starter", set()) & set(dex), key=dex.get)
    rival_only = set()
    if starters:
        alts = []
        for s in starters:
            extra = {s}
            if roamer:
                extra.add(roamer.get(s, roamer["*"]))
            alts.append(closure(base | extra) - base)
        choices.append(alts)
    fossils = sorted(choice_seeds.get("fossil", set()), key=dex.get)
    if fossils:
        choices.append([closure(base | {f}) - base for f in fossils])
    choices = [alts for alts in choices if any(alts)]

    def nums(names):
        return sorted(dex[n] for n in names)

    everything = set(base).union(*[a for alts in choices for a in alts])
    return {
        "required": nums(base),
        "choices": [[nums(a) for a in alts] for alts in choices],
        "unobtainable": [n for n in sorted(dex, key=dex.get) if n not in everything and n not in rival_only],
        "event_islands_open": sorted(open_islands),
        "names": {str(n): name for name, n in sorted(dex.items(), key=lambda kv: kv[1])},
    }


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    out = {"game": sys.argv[2], **analyse(sys.argv[1])}
    complete = len(out["required"]) + sum(max(len(a) for a in alts) for alts in out["choices"])
    print(f"{out['game']}: {len(out['required'])} always obtainable, "
          f"{len(out['choices'])} choices, about {complete} for a complete Pokédex; "
          f"unobtainable: {', '.join(out['unobtainable']) or 'none'}", file=sys.stderr)
    json.dump(out, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
