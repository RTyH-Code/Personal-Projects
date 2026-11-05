#!/usr/bin/env python3
"""Consistency checks for FireRed QoL+Hard's data. Run from the repo root:

    python3 tools/hack/validate.py

Prints every problem found (and exits 1 if there are any). It checks that each
move has data, a name, a description and an animation; that each species has
stats, graphics, learnsets and a Pokedex entry; that learnsets, egg moves,
evolutions, trainer parties and wild encounters only use things that exist;
and that text fits the boxes it is shown in.
"""
import json
import re
import sys

problems = []


def bad(msg):
    problems.append(msg)


def read(p):
    return open(p, encoding="utf-8").read()


def defines(path, prefix):
    out = {}
    for name, val in re.findall(r"#define (%s\w+)\s+(\w+)" % prefix, read(path)):
        out[name] = val
    res = {}
    for name in out:
        v, seen = out[name], set()
        while not v.isdigit() and v in out and v not in seen:
            seen.add(v)
            v = out[v]
        if v.isdigit():
            res[name] = int(v)
    return res


def block_of(text, label):
    i = text.index(label)
    a = text.index("{", i)
    depth, j = 0, a
    while True:
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[a + 1:j]
        j += 1


# ---------------------------------------------------------------- moves
moves = defines("include/constants/moves.h", "MOVE_")
MOVES_COUNT = int(re.search(r"#define MOVES_COUNT (\d+)", read("include/constants/moves.h")).group(1))
move_by_id = {v: k for k, v in moves.items() if k != "MOVE_NONE"}
bm = read("src/data/battle_moves.h")
move_data = dict(re.findall(r"\[(MOVE_\w+)\] =\s*\{(.*?)\n    \},", bm, re.S))
names = dict(re.findall(r'\[(MOVE_\w+)\]\s*= _\("([^"]*)"\)', read("src/data/text/move_names.h")))
md = read("src/move_descriptions.c")
desc_ptr = dict(re.findall(r"\[(MOVE_\w+)\s*- 1\] = (gMoveDescription_\w+)", md))
desc_txt = {n: "".join(re.findall(r'"(.*?)"', b)) for n, b in re.findall(r"const u8 (gMoveDescription_\w+)\[\] = _\((.*?)\);", md, re.S)}
anim_s = read("data/battle_anim_scripts.s")
anim_table = re.findall(r"\t\.4byte (Move_\w+)", anim_s.split("gBattleAnims_Moves::")[1].split("gBattleAnims_StatusConditions")[0])
anim_labels = set(re.findall(r"^(Move_\w+):", anim_s, re.M))
effects = defines("include/constants/battle_move_effects.h", "EFFECT_")
eff_table = re.findall(r"\t\.4byte (BattleScript_\w+)\s+@ (EFFECT_\w+)", read("data/battle_scripts_1.s"))
if len(eff_table) != max(effects.values()) + 1:
    bad(f"battle effect script table has {len(eff_table)} entries for {max(effects.values()) + 1} effects")
for i, (_, e) in enumerate(eff_table):
    if effects.get(e) != i:
        bad(f"battle effect table entry {i} is labelled {e}")
if len(anim_table) < MOVES_COUNT:
    bad(f"move animation table has {len(anim_table)} entries for {MOVES_COUNT} moves")
for i in range(1, MOVES_COUNT):
    m = move_by_id.get(i)
    if not m:
        bad(f"move id {i} has no constant")
        continue
    if m not in move_data:
        bad(f"{m}: no battle data")
    else:
        e = re.search(r"\.effect = (EFFECT_\w+)", move_data[m]).group(1)
        if e not in effects:
            bad(f"{m}: unknown effect {e}")
        pw = int(re.search(r"\.power = (\d+)", move_data[m]).group(1))
        if pw > 255:
            bad(f"{m}: power {pw} > 255")
    if m not in names:
        bad(f"{m}: no name")
    elif len(names[m]) > 12:
        bad(f"{m}: name '{names[m]}' is over 12 characters")
    if m not in desc_ptr:
        bad(f"{m}: no description")
    else:
        lines = desc_txt[desc_ptr[m]].split("\\n")
        if len(lines) > 4 or max(len(l) for l in lines) > 21:
            bad(f"{m}: description doesn't fit ({lines})")
    if i < len(anim_table) and anim_table[i] not in anim_labels:
        bad(f"{m}: animation {anim_table[i]} is not defined")

# ---------------------------------------------------------------- species
spec = defines("include/constants/species.h", "SPECIES_")
NUM_SPECIES = spec["SPECIES_EGG"]
placeholder = {v for k, v in spec.items() if k.startswith("SPECIES_OLD_UNOWN_")}
used_slots = {v for k, v in spec.items() if not k.startswith("SPECIES_OLD_UNOWN_") and v in placeholder}
real = {}
for k, v in spec.items():
    if 0 < v < NUM_SPECIES and k not in ("SPECIES_EGG",) and not k.startswith("SPECIES_UNOWN_"):
        if k.startswith("SPECIES_OLD_UNOWN_") and v not in used_slots:
            continue
        if not k.startswith("SPECIES_OLD_UNOWN_"):
            real[v] = k
species_names = set(real.values())
sinfo = read("src/data/pokemon/species_info.h")
info = dict(re.findall(r"\n    \[(SPECIES_\w+)\] =\s*\n    \{(.*?)\n    \}", sinfo, re.S))
snames = dict(re.findall(r'\[(SPECIES_\w+)\]\s*= _\("([^"]*)"\)', read("src/data/text/species_names.h")))
abil = defines("include/constants/abilities.h", "ABILITY_")
impl_src = read("tools/hack/abilities.py")
impl = {re.sub(r"[^A-Z0-9]+", "_", a.upper()).strip("_") for a in re.findall(r'"([^"]+)"', block_of(impl_src, "IMPLEMENTED ="))}
g = "src/data/pokemon_graphics/"
gfx = {}
for f, pat in (("front_pic_table.h", r"SPECIES_SPRITE\((\w+), (\w+)\)"), ("back_pic_table.h", r"SPECIES_SPRITE\((\w+), (\w+)\)"),
               ("palette_table.h", r"SPECIES_PAL\((\w+), (\w+)\)"), ("shiny_palette_table.h", r"SPECIES_SHINY_PAL\((\w+), (\w+)\)")):
    gfx[f] = {"SPECIES_" + a: b for a, b in re.findall(pat, read(g + f))}
gfx["footprint"] = dict(re.findall(r"\[(SPECIES_\w+)\] = (gMonFootprint_\w+)", read(g + "footprint_table.h")))
icons = dict(re.findall(r"\[(SPECIES_\w+)\]\s*= (gMonIcon_\w+)", read("src/pokemon_icon.c")))
coords_f = set(re.findall(r"\[(SPECIES_\w+)\] =", read(g + "front_pic_coordinates.h")))
coords_b = set(re.findall(r"\[(SPECIES_\w+)\] =", read(g + "back_pic_coordinates.h")))
lu_ptr = dict(re.findall(r"\[(SPECIES_\w+)\] = (s\w+LevelUpLearnset)", read("src/data/pokemon/level_up_learnset_pointers.h")))
lu_txt = read("src/data/pokemon/level_up_learnsets.h")
lu = {n: re.findall(r"LEVEL_UP_MOVE\(\s*(\d+),\s*(MOVE_\w+)\)", b)
      for n, b in re.findall(r"static const u16 (s\w+LevelUpLearnset)\[\] = \{(.*?)\};", lu_txt, re.S)}
tm_entries = set(re.findall(r"\[(SPECIES_\w+)\]\s*= TMHM_LEARNSET", read("src/data/pokemon/tmhm_learnsets.h")))
for sid, sp in sorted(real.items()):
    if sp not in info:
        bad(f"{sp}: no species info")
        continue
    i = info[sp]
    if sp not in snames or snames[sp] in ("?", ""):
        bad(f"{sp}: no name")
    elif len(snames[sp]) > 10:
        bad(f"{sp}: name over 10 letters")
    for a in re.findall(r"ABILITY_\w+", re.search(r"\.abilities = \{(.*?)\}", i).group(1)):
        if a not in abil:
            bad(f"{sp}: unknown ability {a}")
        elif abil[a] > 77 and a[8:] not in impl:
            bad(f"{sp}: ability {a} has no effect in this hack")
    first = re.search(r"\.abilities = \{(\w+)", i).group(1)
    if first == "ABILITY_NONE":
        bad(f"{sp}: first ability slot is empty")
    for f, tab in gfx.items():
        if sp not in tab or "QuestionMark" in tab[sp]:
            bad(f"{sp}: no {f} graphic")
    if sp not in icons or "QuestionMark" in icons[sp]:
        bad(f"{sp}: no icon")
    if sp not in coords_f or sp not in coords_b:
        bad(f"{sp}: no sprite coordinates")
    if sp not in tm_entries:
        bad(f"{sp}: no TM/HM learnset entry")
    arr = lu_ptr.get(sp)
    if not arr or arr not in lu:
        bad(f"{sp}: no level-up learnset")
        continue
    seen = set()
    prev = 0
    for lv, mv in lu[arr]:
        lv = int(lv)
        if mv not in moves:
            bad(f"{sp}: learnset has unknown {mv}")
        if not 1 <= lv <= 100:
            bad(f"{sp}: learns {mv} at level {lv}")
        if lv < prev:
            bad(f"{sp}: learnset not in level order at {mv}")
        prev = lv
        if mv in seen:
            bad(f"{sp}: learns {mv} twice")
        seen.add(mv)
    if len(lu[arr]) > 32:
        bad(f"{sp}: {len(lu[arr])} level-up moves (the relearner reads 32)")

# egg moves
for sp, body in re.findall(r"egg_moves\((\w+),(.*?)\)", read("src/data/pokemon/egg_moves.h"), re.S):
    ms = re.findall(r"MOVE_\w+", body)
    if len(ms) > 10:
        bad(f"egg moves of {sp}: {len(ms)} (the Day Care holds 10)")
    for m in ms:
        if m not in moves:
            bad(f"egg moves of {sp}: unknown {m}")

# evolutions
items = defines("include/constants/items.h", "ITEM_")
item_eff = set(re.findall(r"\[(ITEM_\w+) - ITEM_POTION\]", read("src/data/pokemon/item_effects.h")))
evo_txt = read("src/data/pokemon/evolution.h")
for a, body in re.findall(r"\[(SPECIES_\w+)\]\s*=\s*\{(.*?)\}\},", evo_txt, re.S):
    evs = re.findall(r"\{(EVO_\w+), ([^,]+), (SPECIES_\w+)", body)
    if len(evs) > 8:
        bad(f"{a}: {len(evs)} evolutions (limit 8)")
    for meth, param, t in evs:
        param = param.strip()
        if t not in species_names:
            bad(f"{a} evolves into unknown {t}")
        if meth in ("EVO_ITEM", "EVO_ITEM_MALE", "EVO_ITEM_FEMALE", "EVO_TRADE_ITEM"):
            if param not in items:
                bad(f"{a} -> {t}: unknown item {param}")
            elif meth != "EVO_TRADE_ITEM" and param not in item_eff:
                bad(f"{a} -> {t}: {param} has no item effect, so it can't be used")
        if meth == "EVO_MOVE" and param not in moves:
            bad(f"{a} -> {t}: unknown move {param}")

# Pokedex
dex = read("include/constants/pokedex.h")
nat_vals = defines("include/constants/pokedex.h", "NATIONAL_DEX_")
enum = re.findall(r"(NATIONAL_DEX_\w+),", dex.split("HOENN_DEX_NONE")[0])
for n, nm in enumerate(enum):
    nat_vals.setdefault(nm, n)
for nm, rhs in re.findall(r"#define (NATIONAL_DEX_\w+)\s+(NATIONAL_DEX_\w+)", dex):
    if rhs in nat_vals:
        nat_vals[nm] = nat_vals[rhs]
COUNT = nat_vals["NATIONAL_DEX_COUNT"] if "NATIONAL_DEX_COUNT" in nat_vals else None
entries = read("src/data/pokemon/pokedex_entries.h")
have_entry = set(re.findall(r"\[(NATIONAL_DEX_\w+)\] =", entries))
have_num = {nat_vals[e] for e in have_entry if e in nat_vals}
for n in range(1, COUNT + 1):
    if n not in have_num:
        bad(f"National Dex #{n} (internal) has no Pokedex entry")
texts = read("src/data/pokemon/pokedex_text_fr.h")
for name, body in re.findall(r"const u8 (g\w+PokedexText)\[\] = _\((.*?)\);", texts, re.S):
    lines = "".join(re.findall(r'"(.*?)"', body)).split("\\n")
    if (max(len(l) for l in lines) > 43 or len(lines) > 4) and "REVISION" not in body:
        bad(f"{name}: Pokedex text may not fit ({max(len(l) for l in lines)} chars, {len(lines)} lines)")
orders = read("src/data/pokemon/pokedex_orders.h")
for label, need, kind in (("gPokedexOrder_Alphabetical", COUNT, "NATIONAL_DEX"), ("gPokedexOrder_Type", COUNT, "SPECIES"),
                          ("gPokedexOrder_Weight", COUNT, "NATIONAL_DEX"), ("gPokedexOrder_Height", COUNT, "NATIONAL_DEX")):
    lst = re.findall(r"(%s_\w+)" % kind, block_of(orders, label))
    if len(lst) != need:
        bad(f"{label}: {len(lst)} entries, the game reads {need}")
    if len(set(lst)) != len(lst):
        dup = sorted({x for x in lst if lst.count(x) > 1})
        bad(f"{label}: duplicates {dup}")

# positional species tables in pokemon.c
pc = read("src/pokemon.c")
for table in ("sSpeciesToHoennPokedexNum", "sSpeciesToNationalPokedexNum"):
    body = block_of(pc, f"static const u16 {table}[NUM_SPECIES - 1] =")
    n = len([x for x in body.split(",") if x.strip() and not x.strip().startswith("//")])
    n = len(re.findall(r"^\s*(?:SPECIES_TO_\w+\(\w+\)|HOENN_DEX_\w+|NATIONAL_DEX_\w+|0)\s*,", body, re.M))
    if n != NUM_SPECIES - 1:
        bad(f"{table}: {n} entries for {NUM_SPECIES - 1} species")

# ---------------------------------------------------------------- items
ij = json.load(open("src/data/items.json", encoding="utf-8"))["items"]
ITEMS_COUNT = int(re.search(r"#define ITEMS_COUNT (\d+)", read("include/constants/items.h")).group(1)) if re.search(r"#define ITEMS_COUNT (\d+)", read("include/constants/items.h")) else len(ij)
if len(ij) != ITEMS_COUNT:
    bad(f"items.json has {len(ij)} items, ITEMS_COUNT is {ITEMS_COUNT}")
icon_tab = dict(re.findall(r"\[(ITEM_\w+)\]\s*= \{(gItemIcon_\w+)", read("src/data/item_icon_table.h")))
for n, it in enumerate(ij):
    if it["english"] == "????????" or it["itemId"] == "ITEM_NONE":
        continue
    if len(it["english"]) > 13 and it["itemId"] != "ITEM_POKEBLOCK_CASE":
        bad(f"{it['itemId']}: name over 13 characters")
    for l in it["description_english"].split("\\n"):
        if len(l) > 37:
            bad(f"{it['itemId']}: description line too long: {l!r}")
    if len(it["english"]) > 13 and it["itemId"] == "ITEM_POKEBLOCK_CASE":
        pass  # vanilla
    if items.get(it["itemId"]) != n:
        bad(f"{it['itemId']} is at position {n} in items.json but its constant is {items.get(it['itemId'])}")
    if icon_tab.get(it["itemId"], "gItemIcon_QuestionMark") == "gItemIcon_QuestionMark" and not it["itemId"].startswith(("ITEM_TM", "ITEM_HM")):
        if it["pocket"] != "POCKET_KEY_ITEMS":
            bad(f"{it['itemId']}: no icon")

# ---------------------------------------------------------------- trainers and wild Pokemon
tp = read("src/data/trainer_parties.h")
for party, body in re.findall(r"static const struct \w+ (sParty_\w+)\[\] = \{(.*?)\n\};", tp, re.S):
    for mon in re.findall(r"\{(.*?)\n    \}", body, re.S):
        sp = re.search(r"\.species = (SPECIES_\w+)", mon)
        if not sp or sp.group(1) not in species_names:
            bad(f"{party}: unknown species {sp.group(1) if sp else '?'}")
        lvl = re.search(r"\.lvl = (\d+)", mon)
        if lvl and not 1 <= int(lvl.group(1)) <= 100:
            bad(f"{party}: level {lvl.group(1)}")
        for m in re.findall(r"MOVE_\w+", mon):
            if m not in moves:
                bad(f"{party}: unknown move {m}")
        it = re.search(r"\.heldItem = (ITEM_\w+)", mon)
        if it and it.group(1) not in items:
            bad(f"{party}: unknown item {it.group(1)}")
we = json.load(open("src/data/wild_encounters.json"))
for grp in we["wild_encounter_groups"]:
    for enc in grp["encounters"]:
        for kind in ("land_mons", "water_mons", "rock_smash_mons", "fishing_mons"):
            for m in enc.get(kind, {}).get("mons", []):
                if m["species"] not in species_names:
                    bad(f"{enc.get('base_label')}: unknown wild {m['species']}")
                if not 1 <= m["min_level"] <= m["max_level"] <= 100:
                    bad(f"{enc.get('base_label')}: levels {m['min_level']}-{m['max_level']}")

# ---------------------------------------------------------------- battle strings
ids = defines("include/constants/battle_string_ids.h", "STRINGID_")
ids["BATTLESTRINGS_COUNT"] = int(re.search(r"#define BATTLESTRINGS_COUNT\s+(\d+)", read("include/constants/battle_string_ids.h")).group(1))
m = re.search(r"#define BATTLESTRINGS_TABLE_START\s+(\d+)", read("include/constants/battle_string_ids.h"))
if m:
    ids["BATTLESTRINGS_TABLE_START"] = int(m.group(1))
bmsg = read("src/battle_message.c")
table_ids = set(re.findall(r"\[(STRINGID_\w+) - BATTLESTRINGS_TABLE_START\]", bmsg))
start = ids.get("BATTLESTRINGS_TABLE_START", 12)
for name, v in ids.items():
    if start <= v < ids["BATTLESTRINGS_COUNT"] and name not in table_ids and name not in ("BATTLESTRINGS_TABLE_START",):
        if not any(ids.get(t) == v for t in table_ids):
            bad(f"{name}: no battle string")

for p in problems:
    print(p)
print(f"{len(problems)} problem(s)")
sys.exit(1 if problems else 0)
