#!/usr/bin/env python3
"""Add a later-generation Pokemon to FireRed QoL+Hard in an unused species slot.

    python3 tools/hack/add_species.py <pokemon-showdown>/data <pokeemerald-expansion> NAME

FireRed has 25 unused "old Unown" species slots (252-276). Deoxys's formes use
B-D; new Pokemon take the next free slot. Each gets an internal National Dex
number after Deoxys (387, 388, ...) so the Pokedex, seen/caught flags and save
data need no resizing; the Pokedex and summary screen show its real number.

Stats, types, abilities, learnsets, Pokedex size and the TM/tutor
compatibility come from Showdown's data (read as text, never run). Sprites,
icon, footprint and cry come from pokeemerald-expansion (community-made Gen 3
style graphics; see the credits in the README).

The per-Pokemon details that need a judgement call (evolution method, habitat
page, Pokedex text, sprite positions) are in NEW_SPECIES below.
"""
import os
import re
import shutil
import subprocess
import sys
import textwrap

from PIL import Image

SD, EXP, NAME = sys.argv[1], sys.argv[2], sys.argv[3]

NEW_SPECIES = {
    "WEAVILE": dict(
        slot="OLD_UNOWN_E", dexslot="OLD_UNOWN_B", realnum=461, prevo="SNEASEL",
        evo="{EVO_ITEM, ITEM_RAZOR_CLAW, SPECIES_WEAVILE}",
        habitat=("sDexCategory_ForestPkmn_Page18", "SPECIES_SNEASEL"),
        category="SHARP CLAW", height=11, weight=340, expyield=199,
        text="They live in snowy regions, in groups of\nfour or five, leaving marks on trees and\nrocks. They hunt as a team.",
        scale=(320, 7, 256, 0), front=(56, 56, 4), back=(64, 64, 6), iconpal=0,
        bodycolor="BODY_COLOR_BLACK", itemrare="ITEM_QUICK_CLAW",
    ),
}
S = NEW_SPECIES[NAME]
sdkey = NAME.lower().replace("_", "")
Title = NAME.title().replace("_", "")


def read(p):
    return open(p, encoding="utf-8").read()


def write(p, s):
    open(p, "w", encoding="utf-8").write(s)


def edit(p, old, new, count=1):
    s = read(p)
    assert s.count(old) >= 1, (p, old[:80])
    write(p, s.replace(old, new, count))


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def ts_entry(path, key):
    lines, inside = [], False
    for line in open(path, encoding="utf-8"):
        if re.match(r'^\t"?%s"?: \{$' % key, line.rstrip("\n")):
            inside = True
        elif inside and line.startswith("\t},"):
            break
        elif inside:
            lines.append(line.rstrip("\n"))
    assert lines, key
    return "\n".join(lines)


dex = ts_entry(SD + "/pokedex.ts", sdkey)
stats = dict(re.findall(r"(hp|atk|def|spa|spd|spe): (\d+)", re.search(r"baseStats: \{(.*?)\}", dex).group(1)))
types = ["TYPE_" + t.upper() for t in re.findall(r'"(\w+)"', re.search(r"types: \[(.*?)\]", dex).group(1))]
types = (types * 2)[:2]
abil = dict(re.findall(r'(\w): "([^"]+)"', re.search(r"abilities: \{(.*?)\}", dex).group(1)))
const = lambda a: "ABILITY_" + re.sub(r"[^A-Z0-9]+", "_", a.upper()).strip("_")
abilities = [const(abil["0"]), const(abil["1"]) if "1" in abil else "ABILITY_NONE", const(abil["H"]) if "H" in abil else "ABILITY_NONE"]
learn = {}
in_ls = False
for line in ts_entry(SD + "/learnsets.ts", sdkey).split("\n"):
    m = re.match(r"^\t\t\t(\w+): \[(.*)\],?$", line)
    if m:
        learn[m.group(1)] = re.findall(r'"(\d)([A-Z])(\d*)"', m.group(2))

moves_h = read("include/constants/moves.h")
move_ids = {m: int(n) for m, n in re.findall(r"#define (MOVE_\w+) (\d+)\n", moves_h)}
by_key = {norm(m[5:]): m for m in move_ids}
prevo = S["prevo"]
SP = "SPECIES_" + NAME

# ---------------------------------------------------------------- constants
edit("include/constants/species.h", "#define IS_DEOXYS_FORME(species)",
     f"#define {SP} SPECIES_{S['slot']} // FireRed QoL+Hard: new species (tools/hack/add_species.py)\n#define IS_DEOXYS_FORME(species)")
edit("include/constants/pokedex.h", "#define NATIONAL_DEX_COUNT  NATIONAL_DEX_DEOXYS",
     f"#define NATIONAL_DEX_{NAME} NATIONAL_DEX_{S['dexslot']}\n#define NATIONAL_DEX_COUNT  NATIONAL_DEX_DEOXYS")
s = read("include/constants/pokedex.h")
s = re.sub(r"#define NATIONAL_DEX_COUNT  NATIONAL_DEX_\w+", f"#define NATIONAL_DEX_COUNT  NATIONAL_DEX_{NAME}", s)
write("include/constants/pokedex.h", s)
edit("src/pokemon.c", f"    SPECIES_TO_HOENN({S['slot']}),", f"    HOENN_DEX_{S['dexslot']}, // {NAME}")
edit("src/pokemon.c", f"    SPECIES_TO_NATIONAL({S['slot']}),", f"    NATIONAL_DEX_{S['dexslot']}, // {NAME}")

# ---------------------------------------------------------------- species info and name
p = "src/data/pokemon/species_info.h"
s = read(p)
info = f"""[{SP}] =
    {{
        .baseHP = {stats['hp']},
        .baseAttack = {stats['atk']},
        .baseDefense = {stats['def']},
        .baseSpeed = {stats['spe']},
        .baseSpAttack = {stats['spa']},
        .baseSpDefense = {stats['spd']},
        .types = {{{types[0]}, {types[1]}}},
        .catchRate = 45,
        .expYield = {S['expyield']},
        .evYield_HP = 0,
        .evYield_Attack = 1,
        .evYield_Defense = 0,
        .evYield_Speed = 1,
        .evYield_SpAttack = 0,
        .evYield_SpDefense = 0,
        .itemCommon = ITEM_NONE,
        .itemRare = {S['itemrare']},
        .genderRatio = PERCENT_FEMALE(50),
        .eggCycles = 20,
        .friendship = 35,
        .growthRate = GROWTH_MEDIUM_SLOW,
        .eggGroups = {{EGG_GROUP_FIELD, EGG_GROUP_FIELD}},
        .abilities = {{{', '.join(abilities)}}},
        .safariZoneFleeRate = 0,
        .bodyColor = {S['bodycolor']},
        .noFlip = FALSE,
    }}"""
# copy breeding fields from the pre-evolution so they always match
pre = re.search(r"\[SPECIES_%s\] =\s*\{(.*?)\n    \}" % prevo, s, re.S).group(1)
for field in ("genderRatio", "eggCycles", "friendship", "growthRate", "eggGroups"):
    v = re.search(r"\.%s = (.*?),\n" % field, pre).group(1)
    info = re.sub(r"\.%s = .*?,\n" % field, f".{field} = {v},\n", info)
s = s.replace(f"[SPECIES_{S['slot']}] = OLD_UNOWN_SPECIES_INFO", info, 1)
assert f"[{SP}] =" in s
write(p, s)
edit("src/data/text/species_names.h", f'    [SPECIES_{S["slot"]}] = _("?"),', f'    [{SP}] = _("{NAME}"),')

# ---------------------------------------------------------------- graphics
src = os.path.join(EXP, "graphics/pokemon", NAME.lower())
dst = os.path.join("graphics/pokemon", NAME.lower())
os.makedirs(dst, exist_ok=True)
front = Image.open(os.path.join(src, "anim_front.png"))
front.crop((0, 0, 64, 64)).save(os.path.join(dst, "front.png"))  # FireRed shows one frame
for f in ("back.png", "icon.png", "footprint.png", "normal.pal", "shiny.pal"):
    shutil.copy(os.path.join(src, f), os.path.join(dst, f))
d = f"graphics/pokemon/{NAME.lower()}"
edit("src/data/graphics/pokemon.h", "// Deoxys formes (FireRed QoL+Hard)",
     f"""// {Title} (FireRed QoL+Hard, graphics from pokeemerald-expansion)
const u32 gMonFrontPic_{Title}[] = INCBIN_U32("{d}/front.4bpp.lz");
const u32 gMonBackPic_{Title}[] = INCBIN_U32("{d}/back.4bpp.lz");
const u32 gMonPalette_{Title}[] = INCBIN_U32("{d}/normal.gbapal.lz");
const u32 gMonShinyPalette_{Title}[] = INCBIN_U32("{d}/shiny.gbapal.lz");
const u8 gMonIcon_{Title}[] = INCBIN_U8("{d}/icon.4bpp");
const u8 gMonFootprint_{Title}[] = INCBIN_U8("{d}/footprint.1bpp");

// Deoxys formes (FireRed QoL+Hard)""")
edit("include/graphics.h", "extern const u32 gMonFrontPic_DeoxysAttack[];",
     f"extern const u32 gMonFrontPic_{Title}[];\nextern const u32 gMonBackPic_{Title}[];\nextern const u32 gMonPalette_{Title}[];\n"
     f"extern const u32 gMonShinyPalette_{Title}[];\nextern const u8 gMonIcon_{Title}[];\nextern const u8 gMonFootprint_{Title}[];\n"
     "extern const u32 gMonFrontPic_DeoxysAttack[];")
g = "src/data/pokemon_graphics/"
edit(g + "front_pic_table.h", f"SPECIES_SPRITE({S['slot']}, gMonFrontPic_DoubleQuestionMark)", f"SPECIES_SPRITE({NAME}, gMonFrontPic_{Title})")
edit(g + "back_pic_table.h", f"SPECIES_SPRITE({S['slot']}, gMonBackPic_DoubleQuestionMark)", f"SPECIES_SPRITE({NAME}, gMonBackPic_{Title})")
edit(g + "palette_table.h", f"SPECIES_PAL({S['slot']}, gMonPalette_DoubleQuestionMark)", f"SPECIES_PAL({NAME}, gMonPalette_{Title})")
edit(g + "shiny_palette_table.h", f"SPECIES_SHINY_PAL({S['slot']}, gMonShinyPalette_DoubleQuestionMark)", f"SPECIES_SHINY_PAL({NAME}, gMonShinyPalette_{Title})")
edit(g + "footprint_table.h", f"[SPECIES_{S['slot']}] = gMonFootprint_QuestionMark", f"[{SP}] = gMonFootprint_{Title}")
for f, (w, h, y) in (("front_pic_coordinates.h", S["front"]), ("back_pic_coordinates.h", S["back"])):
    s = read(g + f)
    s, n = re.subn(r"\[SPECIES_%s\] =\n    \{\n        \.size = MON_COORDS_SIZE\(\d+, \d+\),\n        \.y_offset = \d+," % S["slot"],
                   f"[{SP}] =\n    {{\n        .size = MON_COORDS_SIZE({w}, {h}),\n        .y_offset = {y},", s)
    assert n == 1, f
    write(g + f, s)
edit("src/pokemon_icon.c", f"    [SPECIES_{S['slot']}] = gMonIcon_QuestionMark,", f"    [{SP}] = gMonIcon_{Title},")
edit("src/pokemon_icon.c", f"    [SPECIES_{S['slot']}] = 0,", f"    [{SP}] = {S['iconpal']},")
row = re.search(r"\[SPECIES_%s\s*- 1\] = (\{[^}]*\})," % prevo, read("src/menu2.c")).group(1)
s = read("src/menu2.c")
s, n = re.subn(r"\[SPECIES_%s\s*- 1\] = \{[^}]*\}," % S["slot"], f"[{SP} - 1] = {row},", s)
assert n == 1
write("src/menu2.c", s)

# ---------------------------------------------------------------- cry
cries = read("include/constants/hoenn_cries.h")
last = max(int(n) for n in re.findall(r"CRY_\w+ = (\d+),", cries))
cry_id = last + 1
assert cry_id < 512, "the cry tables hold 4 x 128 cries"
edit("include/constants/hoenn_cries.h", f" = {last},\n", f" = {last},\n    CRY_{NAME} = {cry_id},\n")
shutil.copy(os.path.join(EXP, "sound/direct_sound_samples/cries", NAME.lower() + ".wav"),
            f"sound/direct_sound_samples/cries/{NAME.lower()}.wav")
s = read("sound/cry_tables.inc")
lines = s.split("\n")
rev = lines.index("gCryTable_Reverse::")
fwd_last = max(i for i in range(rev) if lines[i].startswith("\tcry "))
lines.insert(fwd_last + 1, f"\tcry Cry_{Title}")
rev_last = max(i for i, l in enumerate(lines) if l.startswith("\tcry_reverse "))
lines.insert(rev_last + 1, f"\tcry_reverse Cry_{Title}")
write("sound/cry_tables.inc", "\n".join(lines))
write("sound/direct_sound_data.inc", read("sound/direct_sound_data.inc").rstrip("\n") +
      f'\n\n\t.align 2\nCry_{Title}::\n\t.incbin "sound/direct_sound_samples/cries/{NAME.lower()}.bin"\n')
edit("src/pokemon.c", "    if (species < SPECIES_OLD_UNOWN_B - 1)\n        return species;",
     f"    if (species == {SP} - 1)\n        return CRY_{NAME};\n    if (species < SPECIES_OLD_UNOWN_B - 1)\n        return species;")

# ---------------------------------------------------------------- learnsets
gen = max((g for e in learn.values() for g, k, _ in e if k == "L" and g in "789"), default="9")
lu = sorted({(max(1, int(lvl)), by_key[k]) for k, e in learn.items() if k in by_key
             for g, kind, lvl in e if kind == "L" and g == gen}, key=lambda e: (e[0], move_ids[e[1]]))
seen, lu2 = set(), []
for lv, mv in lu:
    if mv not in seen:
        seen.add(mv)
        lu2.append((lv, mv))
lu2 = lu2[:32]
p = "src/data/pokemon/level_up_learnsets.h"
s = read(p)
slotnum = re.search(r"#define SPECIES_%s (\d+)" % S["slot"], read("include/constants/species.h")).group(1)
old = re.search(r"static const u16 sSpecies%sLevelUpLearnset\[\] = \{.*?\};" % slotnum, s, re.S).group(0)
s = s.replace(old, f"static const u16 s{Title}LevelUpLearnset[] = {{\n" +
              "".join(f"    LEVEL_UP_MOVE({lv:2d}, {mv}),\n" for lv, mv in lu2) + "    LEVEL_UP_END\n};")
write(p, s)
edit("src/data/pokemon/level_up_learnset_pointers.h", f"[SPECIES_{S['slot']}] = sSpecies{slotnum}LevelUpLearnset",
     f"[{SP}] = s{Title}LevelUpLearnset")


def learns(key):
    return any(kind in "MTL" for g, kind, _ in learn.get(key, []))


# TMs/HMs and FireRed's move tutors: the pre-evolution's, plus any the modern data allows
p = "src/data/pokemon/tmhm_learnsets.h"
s = read(p)
pre_tm = re.findall(r"TMHM\(((?:TM|HM)\d\d_\w+)\)", re.search(r"\[SPECIES_%s\]\s*= TMHM_LEARNSET\((.*?)\),\n" % prevo, s, re.S).group(1))
all_tm = sorted(set(re.findall(r"TMHM\(((?:TM|HM)\d\d_\w+)\)", s)), key=lambda t: (t[:2] == "HM", t))
tms = [t for t in all_tm if t in pre_tm or learns(norm(t.split("_", 1)[1]))]
body = "\n".join(f"{'' if i == 0 else ' ' * 40 + '| '}TMHM({t})" for i, t in enumerate(tms))
s = s.replace(f"[SPECIES_{S['slot']}] = TMHM_LEARNSET(0)", f"[{SP}] = TMHM_LEARNSET({body})", 1)
assert f"[{SP}] = TMHM_LEARNSET(" in s
write(p, s)
p = "src/data/pokemon/tutor_learnsets.h"
s = read(p)
tut_all = []
for m in re.findall(r"TUTOR\((MOVE_\w+)\)", s):
    if m not in tut_all:
        tut_all.append(m)
pre_t = re.findall(r"TUTOR\((MOVE_\w+)\)", re.search(r"\[SPECIES_%s\] = (.*?),\n\n" % prevo, s, re.S).group(1))
tut = [m for m in tut_all if m in pre_t or learns(norm(m[5:]))]
entry = f"    [{SP}] = " + "\n            | ".join(f"TUTOR({m})" for m in tut) + ",\n\n"
anchor = f"    [SPECIES_{prevo}] = "
i = s.index(anchor)
j = s.index(",\n\n", i) + 3
s = s[:j] + entry + s[j:]
write(p, s)

# modern tutor (Gen 4-9 TM/tutor moves from MOVE_FAIRY_WIND on)
p = "src/data/pokemon/hack_tutor_learnsets.h"
s = read(p)
first = move_ids[re.search(r"#define HACK_TUTOR_FIRST_MOVE (MOVE_\w+)", s).group(1)]
nbytes = int(re.search(r"#define HACK_TUTOR_BYTES (\d+)", s).group(1))
bits = [0] * nbytes
for k, e in learn.items():
    if k in by_key and move_ids[by_key[k]] >= first and any(kind in "MT" and g in "456789" for g, kind, _ in e):
        n = move_ids[by_key[k]] - first
        bits[n // 8] |= 1 << (n % 8)
k = s.rstrip().rindex("};")
s = s[:k] + f"    [{SP}] = {{{', '.join('0x%02X' % b for b in bits)}}},\n" + s[k:]
write(p, s)

# evolution
p = "src/data/pokemon/evolution.h"
s = read(p)
m = re.search(r"    \[SPECIES_%s\]\s*= \{(.*?)\},\n" % prevo, s)
if m:
    s = s.replace(m.group(0), m.group(0).replace("}},\n", "}, " + S["evo"] + "},\n"))
else:
    s = s.replace("    [SPECIES_GOLBAT]", f"    [SPECIES_{prevo}] = {{{S['evo']}}},\n    [SPECIES_GOLBAT]", 1)
write(p, s)

# ---------------------------------------------------------------- Pokedex
nat = f"NATIONAL_DEX_{NAME}"
text = S["text"].split("\n")
write("src/data/pokemon/pokedex_text_fr.h", read("src/data/pokemon/pokedex_text_fr.h").rstrip("\n") +
      f'\n\nconst u8 g{Title}PokedexText[] = _(\n' + "\n".join(f'    "{l}\\n"' for l in text[:-1]) +
      f'\n    "{text[-1]}");\n\nconst u8 g{Title}PokedexTextUnused[] = _("");\n')
p = "src/data/pokemon/pokedex_entries.h"
s = read(p).rstrip()
assert s.endswith("};")
sc = S["scale"]
s = s[:-2].rstrip() + f"""

    [{nat}] =
    {{
        .categoryName = _("{S['category']}"),
        .height = {S['height']},
        .weight = {S['weight']},
        .description = g{Title}PokedexText,
        .unusedDescription = g{Title}PokedexTextUnused,
        .pokemonScale = {sc[0]},
        .pokemonOffset = {sc[1]},
        .trainerScale = {sc[2]},
        .trainerOffset = {sc[3]},
    }},
}};
"""
write(p, s)

# Pokedex orders: alphabetical (move the placeholder entry), weight and height (insert), type (species list)
p = "src/data/pokemon/pokedex_orders.h"
s = read(p)
ents = re.findall(r"\[(NATIONAL_DEX_\w+)\] =\s*\{\s*\.categoryName = _\(\"[^\"]*\"\),\s*\.height = (\d+),\s*\.weight = (\d+)",
                  read("src/data/pokemon/pokedex_entries.h"))
hw = {n: (int(h), int(w)) for n, h, w in ents}
names = {f"NATIONAL_DEX_{m}": n for m, n in re.findall(r'\[SPECIES_(\w+)\] = _\("([^"]*)"\)', read("src/data/text/species_names.h"))}
names[nat] = NAME


def list_body(label):
    i = s.index(f"const u16 {label}[] =")
    a = s.index("{", i) + 1
    b = s.index("};", a)
    return a, b


a, b = list_body("gPokedexOrder_Alphabetical")
items = [x.strip() for x in s[a:b].split(",") if x.strip()]
items.remove(f"NATIONAL_DEX_{S['dexslot']}")
pos = next(i for i, x in enumerate(items) if x in names and names[x] > NAME and not x.startswith("NATIONAL_DEX_OLD"))
items.insert(pos, nat)
s = s[:a] + "\n" + ",\n".join("    " + x for x in items) + "\n" + s[b:]
for label, idx in (("gPokedexOrder_Weight", 1), ("gPokedexOrder_Height", 0)):
    a, b = list_body(label)
    items = [x.strip() for x in s[a:b].split(",") if x.strip()]
    mine = (S["height"], S["weight"])[idx]
    pos = next((i for i, x in enumerate(items) if x in hw and hw[x][idx] > mine), len(items))
    items.insert(pos, nat)
    s = s[:a] + "\n" + ",\n".join("    " + x for x in items) + "\n" + s[b:]
a, b = list_body("gPokedexOrder_Type")
items = [x.strip() for x in s[a:b].split(",") if x.strip()]
items.remove(f"SPECIES_{S['slot']}")
items.insert(items.index(f"SPECIES_{prevo}") + 1, SP)
s = s[:a] + "\n" + ",\n".join("    " + x for x in items) + "\n" + s[b:]
write(p, s)

page, after = S["habitat"]
edit("src/data/pokemon/pokedex_categories.h", f"static const u16 {page}[] = {{", f"static const u16 {page}[] = {{")
s = read("src/data/pokemon/pokedex_categories.h")
i = s.index(f"static const u16 {page}[] = {{")
j = s.index("};", i)
blk = s[i:j]
assert blk.count("SPECIES_") < 4, "habitat page is full"
s = s[:i] + blk.replace(f"    {after},\n", f"    {after},\n    {SP},\n") + s[j:]
write("src/data/pokemon/pokedex_categories.h", s)

# real National Dex number for display
p = "src/pokemon.c"
s = read(p)
if "Hack_DisplayDexNum" not in s:
    s = s.replace("u16 SpeciesToPokedexNum(u16 species)\n{", """// FireRed QoL+Hard: Pokemon added after Deoxys show their real National Dex number
static const u16 sHackRealDexNums[] = {
};

u16 Hack_DisplayDexNum(u16 dexNum)
{
    if (dexNum > NATIONAL_DEX_DEOXYS && dexNum - NATIONAL_DEX_DEOXYS - 1 < ARRAY_COUNT(sHackRealDexNums))
        return sHackRealDexNums[dexNum - NATIONAL_DEX_DEOXYS - 1];
    return dexNum;
}

u16 SpeciesToPokedexNum(u16 species)
{""", 1)
s = s.replace("static const u16 sHackRealDexNums[] = {\n", f"static const u16 sHackRealDexNums[] = {{\n    [NATIONAL_DEX_{NAME} - NATIONAL_DEX_DEOXYS - 1] = {S['realnum']},\n", 1)
write(p, s)
print(f"added {NAME}: {len(lu2)} level-up moves, {len(tms)} TMs/HMs, {len(tut)} tutor moves, cry {cry_id}")

# display hooks (first run only)
if "Hack_DisplayDexNum" not in read("include/pokemon.h"):
    edit("include/pokemon.h", "u16 SpeciesToPokedexNum(u16 species);", "u16 SpeciesToPokedexNum(u16 species);\nu16 Hack_DisplayDexNum(u16 dexNum);")
    edit("src/pokedex_screen.c", "    u16 dexNum = SpeciesToNationalPokedexNum(species);\n    DexScreen_AddTextPrinterParameterized(windowId, fontId, gText_PokedexNo, x, y, 0);",
         "    u16 dexNum = Hack_DisplayDexNum(SpeciesToNationalPokedexNum(species));\n    DexScreen_AddTextPrinterParameterized(windowId, fontId, gText_PokedexNo, x, y, 0);")
    edit("src/pokemon_summary_screen.c", "    dexNum = SpeciesToPokedexNum(GetMonData(&sMonSummaryScreen->currentMon, MON_DATA_SPECIES));",
         "    dexNum = SpeciesToPokedexNum(GetMonData(&sMonSummaryScreen->currentMon, MON_DATA_SPECIES));\n    if (dexNum != 0xFFFF)\n        dexNum = Hack_DisplayDexNum(dexNum);")

# ---------------------------------------------------------------- evolution items
EVO_ITEMS = {
    "RAZOR_CLAW": dict(slot="ITEM_035", name="RAZOR CLAW", price=2100, hold="HOLD_EFFECT_SCOPE_LENS",
                       desc="A sharply hooked claw that boosts\\\\nthe holder's critical-hit ratio.\\\\nIt can make SNEASEL evolve.",
                       shop="CeladonCity_DepartmentStore_4F", after="ITEM_UP_GRADE"),
}
for item, I in EVO_ITEMS.items():
    if f"ITEM_{item}" in S["evo"] and f"#define ITEM_{item} " not in read("include/constants/items.h"):
        T = item.title().replace("_", "")
        low = item.lower()
        edit("include/constants/items.h", f"#define {I['slot']} ", f"#define ITEM_{item} {I['slot']} // FireRed QoL+Hard\n#define {I['slot']} ")
        s = read("src/data/items.json")
        blocks = list(re.finditer(r"    \{\n.*?\n    \}", s, re.S))
        idx = int(re.search(r"#define %s (\d+)" % I["slot"], read("include/constants/items.h")).group(1))
        blk = blocks[idx]
        assert '"????????"' in blk.group(0), blk.group(0)[:80]
        new = blk.group(0)
        for k, v in (("english", f'"{I["name"]}"'), ("itemId", f'"ITEM_{item}"'), ("price", str(I["price"])),
                     ("holdEffect", f'"{I["hold"]}"'), ("description_english", f'"{I["desc"]}"'),
                     ("pocket", '"POCKET_ITEMS"'), ("type", '"ITEM_TYPE_PARTY_MENU"'), ("fieldUseFunc", '"FieldUseFunc_EvoItem"')):
            new, n = re.subn(r'("%s": )[^,\n]*' % k, lambda m: m.group(1) + v, new, count=1)
            assert n == 1, k
        s = s[:blk.start()] + new + s[blk.end():]
        write("src/data/items.json", s)
        shutil.copy(os.path.join(EXP, f"graphics/items/icons/{low}.png"), f"graphics/items/icons/{low}.png")
        shutil.copy(os.path.join(EXP, f"graphics/items/icon_palettes/{low}.pal"), f"graphics/items/icon_palettes/{low}.pal")
        edit("src/data/graphics/items.h", "const u32 gItemIcon_UpGrade[]",
             f'const u32 gItemIcon_{T}[] = INCBIN_U32("graphics/items/icons/{low}.4bpp.lz");\n'
             f'const u32 gItemIconPalette_{T}[] = INCBIN_U32("graphics/items/icon_palettes/{low}.gbapal.lz");\n\nconst u32 gItemIcon_UpGrade[]')
        edit("include/graphics.h", "extern const u32 gItemIcon_UpGrade[];",
             f"extern const u32 gItemIcon_{T}[];\nextern const u32 gItemIconPalette_{T}[];\nextern const u32 gItemIcon_UpGrade[];")
        edit("src/data/item_icon_table.h", f"    [{I['slot']}]            = {{gItemIcon_QuestionMark, gItemIconPalette_QuestionMark}},",
             f"    [ITEM_{item}]     = {{gItemIcon_{T}, gItemIconPalette_{T}}},")
        edit("src/data/pokemon/item_effects.h", "    [ITEM_UP_GRADE - ITEM_POTION]       = sItemEffect_FireStone, // same effect as every stone\n",
             "    [ITEM_UP_GRADE - ITEM_POTION]       = sItemEffect_FireStone, // same effect as every stone\n"
             f"    [ITEM_{item} - ITEM_POTION]    = sItemEffect_FireStone, // same effect as every stone\n")
        edit(f"data/maps/{I['shop']}/scripts.inc", f"\t.2byte {I['after']}\n", f"\t.2byte {I['after']}\n\t.2byte ITEM_{item}\n")
        print("added item", item)

