#!/usr/bin/env python3
"""Trainer Tower competitive teams.

Rebuilds every Trainer Tower Pokemon as a competitive set, the way real
teams are built:
  - Fully evolved, one of each species per team. When a team's family is
    used up, another fully evolved Pokemon of the same type stands in.
  - Moves from Pokemon Showdown's role-based random-battle sets: Gen 9
    doubles sets on Double floors, Gen 9 singles sets elsewhere, then Gen 3.
    Moves must exist in this hack and be learnable by the species.
  - 252/252 EVs and a nature that fit the role, perfect IVs, a matching
    ability and a role-based held item (no duplicate items on one team).
Opponent levels still scale to your strongest Pokemon, as in the original.

usage: python3 tools/hack/tower_sets.py <dir with gen9_sets.json,
       gen9_doubles-sets.json and gen3..gen8 _sets.json from
       Showdown's data/random-battles/genN/>
The JSON files are read as data only. Runs once; refuses to run twice.
"""
import hashlib, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from learnsets import learnable, move_ids, read  # noqa: E402

if len(sys.argv) != 2:
    sys.exit(__doc__)
FALLBACK = ["gen8", "gen7", "gen6", "gen5", "gen4", "gen3"]
SETS = {name: json.load(open(os.path.join(sys.argv[1], f), encoding="utf-8"))
        for name, f in [("singles", "gen9_sets.json"), ("doubles", "gen9_doubles-sets.json")]
        + [(g, g + "_sets.json") for g in FALLBACK]}
P = "src/trainer_tower_sets.c"
src = read(P)
if "FireRed QoL+Hard: competitive" in src:
    sys.exit("The Trainer Tower teams are already competitive.")


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


ALIASES = {"feintattack": "faintattack", "highjumpkick": "hijumpkick", "smellingsalts": "smellingsalt",
           "visegrip": "vicegrip", "softboiled": "softboiled", "solarbeam": "solarbeam",
           "thunderpunch": "thunderpunch", "doubleedge": "doubleedge", "selfdestruct": "selfdestruct"}
MOVE_BY_NORM = {norm(m[5:]): m for m in move_ids}

# ---------------------------------------------------------------- game data
info = read("src/data/pokemon/species_info.h")
stats, abilities = {}, {}
for sp, body in re.findall(r"\[(SPECIES_\w+)\]\s*=\s*\{(.*?)\n    \}", info, re.S):
    b = {k: int(v) for k, v in re.findall(r"\.base(\w+) = (\d+)", body)}
    if b:
        stats[sp] = b
    a = re.search(r"\.abilities = \{([^}]*)\}", body)
    if a:
        abilities[sp] = [x.strip() for x in a.group(1).split(",")]
moves_txt = read("src/data/battle_moves.h")
MOVES = {}
for m, body in re.findall(r"\[(MOVE_\w+)\]\s*=\s*\{(.*?)\n    \}", moves_txt, re.S):
    power = int(re.search(r"\.power = (\d+)", body).group(1))
    split = re.search(r"\.split = (\w+)", body)
    target = re.search(r"\.target = (\w+)", body).group(1)
    MOVES[m] = (power, split.group(1) if split else "SPLIT_STATUS", target)
evo = read("src/data/pokemon/evolution.h")
evolves = {}
for sp, body in re.findall(r"\[(SPECIES_\w+)\]\s*=\s*\{(.*?)\}\},", evo, re.S):
    evolves[sp] = re.findall(r"(SPECIES_\w+)\}", body + "}")
names = dict(re.findall(r'\[(SPECIES_\w+)\]\s*=\s*_\("([^"]*)"\)', read("src/data/text/species_names.h")))
item_ids = set(re.findall(r"#define (ITEM_\w+)", read("include/constants/items.h")))


def finals(sp, depth=0):
    out = []
    for t in evolves.get(sp, []):
        if t in stats and depth < 4:
            out += finals(t, depth + 1) or [t]
    return out


def showdown_key(sp):
    return norm(names.get(sp, sp[8:]).replace("♀", "f").replace("♂", "m"))


def pick(seq, seed):
    return seq[int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(seq)]


TYPE_ITEM = {"FIRE": "ITEM_CHARCOAL", "WATER": "ITEM_MYSTIC_WATER", "ELECTRIC": "ITEM_MAGNET",
             "GRASS": "ITEM_MIRACLE_SEED", "ICE": "ITEM_NEVER_MELT_ICE", "FIGHTING": "ITEM_BLACK_BELT",
             "POISON": "ITEM_POISON_BARB", "GROUND": "ITEM_SOFT_SAND", "FLYING": "ITEM_SHARP_BEAK",
             "PSYCHIC": "ITEM_TWISTED_SPOON", "BUG": "ITEM_SILVER_POWDER", "ROCK": "ITEM_HARD_STONE",
             "GHOST": "ITEM_SPELL_TAG", "DRAGON": "ITEM_DRAGON_FANG", "DARK": "ITEM_BLACK_GLASSES",
             "STEEL": "ITEM_METAL_COAT", "NORMAL": "ITEM_SILK_SCARF"}
move_type = {m: re.search(r"\.type = TYPE_(\w+)", b).group(1)
             for m, b in re.findall(r"\[(MOVE_\w+)\]\s*=\s*\{(.*?)\n    \}", moves_txt, re.S)}
NATURE = {"HARDY": 0, "LONELY": 1, "BRAVE": 2, "ADAMANT": 3, "NAUGHTY": 4, "BOLD": 5, "DOCILE": 6,
          "RELAXED": 7, "IMPISH": 8, "LAX": 9, "TIMID": 10, "HASTY": 11, "SERIOUS": 12, "JOLLY": 13,
          "NAIVE": 14, "MODEST": 15, "MILD": 16, "QUIET": 17, "BASHFUL": 18, "RASH": 19, "CALM": 20,
          "GENTLE": 21, "SASSY": 22, "CAREFUL": 23, "QUIRKY": 24}


def build(sp, doubles, seed, old_moves, used_items):
    key = showdown_key(sp)
    can = learnable(sp)
    sources = (["doubles"] if doubles else []) + ["singles"] + FALLBACK
    role, abil_names, pool = "", [], []
    for src_name in sources:
        entry = SETS[src_name].get(key)
        if not entry:
            continue
        s = pick(entry["sets"], seed + src_name)
        got = []
        for mv in s["movepool"]:
            n = norm(mv)
            if n.startswith("hiddenpower"):
                continue
            m = MOVE_BY_NORM.get(ALIASES.get(n, n))
            if m and m in can and m not in pool and m not in got:
                got.append(m)
        if got and not role:
            role, abil_names = s["role"], s.get("abilities", [])
        got.sort(key=lambda m: hashlib.md5((seed + m).encode()).hexdigest())
        pool += got
        if len(pool) >= 6:
            break
    pool += [m for m in old_moves if m != "MOVE_NONE" and m in can and m not in pool]

    def is_attack(m):
        return m in MOVES and MOVES[m][0] > 0

    chosen = []
    if doubles and "MOVE_PROTECT" in pool:
        chosen.append("MOVE_PROTECT")
    support_role = "Support" in role or role == "Staller"
    for m in [m for m in pool if is_attack(m)][: (1 if support_role else 2)]:
        chosen.append(m)
    for m in pool:
        if len(chosen) >= 4:
            break
        if m not in chosen:
            chosen.append(m)
    while len(chosen) < 4:
        chosen.append("MOVE_NONE")
    role = role or "original moves"

    if not any(is_attack(m) for m in chosen):
        # Make sure every set can do damage: add its best same-type attack.
        types = stats_types(sp)
        best = max((m for m in can if is_attack(m) and move_type.get(m) in types),
                   key=lambda m: MOVES[m][0], default=None)
        if best:
            slot_i = next((i for i, m in enumerate(chosen) if m != "MOVE_PROTECT"), 3)
            chosen[slot_i] = best
    damaging = [m for m in chosen if m in MOVES and MOVES[m][0] > 0]
    phys = sum(MOVES[m][1] == "SPLIT_PHYSICAL" for m in damaging)
    spec = len(damaging) - phys
    b = stats[sp]
    bulky = (role.startswith("Bulky") or "Support" in role or role in ("Staller", "Doubles Bulky Attacker")
             or (role == "original moves" and len(damaging) <= 1))
    trick_room = "Trick Room" in role or "MOVE_TRICK_ROOM" in chosen
    physical = phys > spec or (phys == spec and b["Attack"] >= b["SpAttack"])
    ev = dict(hp=0, attack=0, defense=0, speed=0, spAttack=0, spDefense=0)
    if bulky:
        ev["hp"] = 252
        if b["Defense"] >= b["SpDefense"]:
            ev["defense"], ev["spDefense"] = 252, 6
            nature = "IMPISH" if physical else "BOLD"
        else:
            ev["spDefense"], ev["defense"] = 252, 6
            nature = "CAREFUL" if physical else "CALM"
    else:
        ev["attack" if physical else "spAttack"] = 252
        if trick_room:
            ev["hp"] = 252
            nature = "BRAVE" if physical else "QUIET"
        else:
            ev["speed"] = 252
            ev["hp"] = 6
            fast = b["Speed"] >= 80
            nature = ("JOLLY" if fast else "ADAMANT") if physical else ("TIMID" if fast else "MODEST")

    # Held item, never repeated on one team.
    stab = [move_type[m] for m in damaging if move_type.get(m) in stats_types(sp)]
    options = []
    if doubles:
        options += ["ITEM_SITRUS_BERRY", "ITEM_LUM_BERRY"]
    if bulky:
        options += ["ITEM_LEFTOVERS", "ITEM_SITRUS_BERRY", "ITEM_SHELL_BELL"]
    else:
        if physical and len(damaging) == 4:
            options.append("ITEM_CHOICE_BAND")
        if stab and stab[0] in TYPE_ITEM:
            options.append(TYPE_ITEM[stab[0]])
        options += ["ITEM_LUM_BERRY", "ITEM_LEFTOVERS", "ITEM_SCOPE_LENS", "ITEM_SHELL_BELL", "ITEM_QUICK_CLAW"]
    options += ["ITEM_LEFTOVERS", "ITEM_SITRUS_BERRY", "ITEM_LUM_BERRY", "ITEM_SHELL_BELL", "ITEM_WHITE_HERB",
                "ITEM_MENTAL_HERB", "ITEM_BRIGHT_POWDER", "ITEM_KINGS_ROCK"]
    item = next(i for i in options if i in item_ids and i not in used_items)
    used_items.add(item)

    ab = abilities.get(sp, ["ABILITY_NONE"])
    want = {"ABILITY_" + re.sub(r"[^A-Z0-9]+", "_", a.upper()).strip("_") for a in abil_names}
    slot = 1 if len(ab) > 1 and ab[1] in want and ab[0] not in want and ab[1] != "ABILITY_NONE" else 0
    return chosen, ev, nature, item, slot, role


def stats_types(sp):
    body = re.search(r"\[" + sp + r"\]\s*=\s*\{(.*?)\n    \}", info, re.S).group(1)
    t = re.search(r"\.types = \{TYPE_(\w+), TYPE_(\w+)\}", body)
    return {t.group(1), t.group(2)} if t else set()


# Stand-ins that fit the trainer better than the automatic pick (Eeveelution
# twins, a Water trainer, a tech trainer, a Ghost/Poison trainer).
STAND_INS = {"SPECIES_UMBREON": ["SPECIES_GLACEON", "SPECIES_LEAFEON"], "SPECIES_MANTINE": ["SPECIES_KINGDRA"],
             "SPECIES_PORYGON": ["SPECIES_AMPHAROS"], "SPECIES_HAUNTER": ["SPECIES_DUSKNOIR"],
             "SPECIES_GYARADOS": ["SPECIES_FERALIGATR"]}
stand_ins_used = set()

# ---------------------------------------------------------------- rewrite every floor
# Each trainer has a pool of six; single floors send out two of them, double
# floors one from each of two trainers, knockout floors one per trainer.
report = []
used = {}  # trainer (by position) -> (species, items)
starts = [(m.start(), m.group(1)) for m in re.finditer(r'\.name = _\("([^"]*)"\)', src)]
types = [(m.start(), m.group(1)) for m in re.finditer(r"\.challengeType = (\w+)", src)]


def last_before(seq, pos):
    best = None
    for p, v in seq:
        if p < pos:
            best = (p, v)
    return best


def do_mon(mm):
    mon = mm.group(0)
    sp = "SPECIES_" + re.search(r"\.species = SPECIES_(\w+)", mon).group(1)
    if sp == "SPECIES_NONE":
        return mon
    tpos, tname = last_before(starts, mm.start())
    doubles = last_before(types, mm.start())[1] == "CHALLENGE_TYPE_DOUBLE"
    used_species, used_items = used.setdefault(tpos, (set(), set()))
    options = [o for o in (finals(sp) or [sp]) if o not in used_species]
    if options:
        new_sp = pick(options, tname + sp)
    else:
        # The family is used up on this team: another fully evolved,
        # non-legendary Pokemon that shares a type, so the theme holds.
        # Hand-picked stand-ins keep a trainer's theme; each one is used once.
        hand = [o for o in STAND_INS.get(sp, []) if o not in used_species and o not in stand_ins_used]
        if hand:
            new_sp = hand[0]
            stand_ins_used.add(new_sp)
        else:
            want = stats_types((finals(sp) or [sp])[0])
            alts = sorted(o for o in stats if not evolves.get(o) and o not in used_species
                          and 470 <= sum(stats[o].values()) < 580 and stats_types(o) & want)
            new_sp = pick(alts, tname + sp)
    used_species.add(new_sp)
    old_moves = re.findall(r"MOVE_\w+", re.search(r"\.moves = \{([^}]*)\}", mon).group(1))
    moves, ev, nature, item, slot, role = build(new_sp, doubles, tname + new_sp, old_moves, used_items)
    report.append(f"{tname:<11} {'D' if doubles else 'S'} {new_sp[8:]:<11} {role:<24} {item[5:]:<14} {nature:<8} " +
                  ", ".join(x[5:] for x in moves))
    mon = mon.replace(f".species = {sp}", f".species = {new_sp}")
    mon = re.sub(r"\.heldItem = \w+", f".heldItem = {item}", mon)
    mon = re.sub(r"\.moves = \{[^}]*\}", ".moves = {%s}" % ", ".join(moves), mon)
    for stat, val in ev.items():
        mon = re.sub(r"\.%sEV = \d+" % stat, f".{stat}EV = {val}", mon)
        mon = re.sub(r"\.%sIV = \d+" % stat, f".{stat}IV = 31", mon)
    mon = re.sub(r"\.abilityNum = \d+", f".abilityNum = {slot}", mon)
    old_p = int(re.search(r"\.personality = (0x[0-9A-Fa-f]+|\d+)", mon).group(1), 0)
    pers = old_p - old_p % 25 + NATURE[nature]
    mon = re.sub(r"\.personality = (0x[0-9A-Fa-f]+|\d+),[^\n]*", f".personality = 0x{pers:X}, // {nature}", mon)
    mon = re.sub(r'\.nickname = _\("[^"]*"\)', f'.nickname = _("{names.get(new_sp, new_sp[8:])}")', mon)
    return mon


new = re.sub(r"\{\s*\n\s*\.species = SPECIES_\w+,.*?\.friendship = \d+\s*\n\s*\}", do_mon, src, flags=re.S)
new = new.replace('#include "global.h"\n', '#include "global.h"\n// FireRed QoL+Hard: competitive Trainer Tower teams (tools/hack/tower_sets.py)\n', 1)
open(P, "w", encoding="utf-8").write(new)
print("\n".join(report))
print(f"\n{len(report)} Trainer Tower Pokemon rebuilt.")
