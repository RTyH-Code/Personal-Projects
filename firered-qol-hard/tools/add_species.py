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

# prevo, evolution, real National Dex number, and an in-game name if the real one is over 10 letters
NEW_SPECIES = {
    "WEAVILE": dict(prevo="SNEASEL", evo="EVO_ITEM, ITEM_RAZOR_CLAW", realnum=461),
    "MAGNEZONE": dict(prevo="MAGNETON", evo="EVO_ITEM, ITEM_THUNDER_STONE", realnum=462, text="Exposure to a special magnetic field\nchanged MAGNETON's molecular structure,\nturning it into MAGNEZONE."),
    "LICKILICKY": dict(prevo="LICKITUNG", evo="EVO_MOVE, MOVE_ROLLOUT", realnum=463, text="Its strange tongue seems to be made of\nunknown materials. Its saliva can\ndissolve anything."),
    "RHYPERIOR": dict(prevo="RHYDON", evo="EVO_ITEM, ITEM_PROTECTOR", realnum=464, text="It puts rocks in holes in its palms and\nuses its muscles to shoot them. GEODUDE\nare sometimes shot by mistake."),
    "TANGROWTH": dict(prevo="TANGELA", evo="EVO_MOVE, MOVE_ANCIENT_POWER", realnum=465, text="It ensnares prey by extending arms made\nof vines. Losing arms to predators\ndoes not trouble it."),
    "ELECTIVIRE": dict(prevo="ELECTABUZZ", evo="EVO_ITEM, ITEM_ELECTIRIZER", realnum=466, text="It pushes the tips of its two tails\nagainst a foe, then lets loose with\nover 20,000 volts of power."),
    "MAGMORTAR": dict(prevo="MAGMAR", evo="EVO_ITEM, ITEM_MAGMARIZER", realnum=467, text="It blasts fireballs of over 3,600\ndegrees from the ends of its arms.\nIt lives in volcanic craters."),
    "TOGEKISS": dict(prevo="TOGETIC", evo="EVO_ITEM, ITEM_SHINY_STONE", realnum=468, text="It shares many blessings with people\nwho respect one another's rights and\navoid needless strife."),
    "YANMEGA": dict(prevo="YANMA", evo="EVO_MOVE, MOVE_ANCIENT_POWER", realnum=469, text="This six-legged POKéMON is easily\ncapable of carrying an adult in flight.\nIts wings beat at high speed."),
    "GLISCOR": dict(prevo="GLIGAR", evo="EVO_ITEM, ITEM_RAZOR_FANG", realnum=472, text="It observes prey while hanging upside\ndown from branches. When the chance\npresents itself, it swoops!"),
    "MAMOSWINE": dict(prevo="PILOSWINE", evo="EVO_MOVE, MOVE_ANCIENT_POWER", realnum=473, text="A frozen MAMOSWINE was dug from ice\ndating back 10,000 years. This POKéMON\nhas been around a long, long time."),
    "PORYGON_Z": dict(prevo="PORYGON2", evo="EVO_ITEM, ITEM_DUBIOUS_DISC", realnum=474, name="PORYGON-Z", text="Additional software was installed to\nmake it a better POKéMON. It began\nacting oddly, however."),
    "DUSKNOIR": dict(prevo="DUSCLOPS", evo="EVO_ITEM, ITEM_REAPER_CLOTH", realnum=477, text="The antenna on its head captures radio\nwaves from the spirit world that tell\nit to take people there."),
    "HONCHKROW": dict(prevo="MURKROW", evo="EVO_ITEM, ITEM_DUSK_STONE", realnum=430, text="Becoming active at night, it is known\nto swarm with numerous MURKROW in tow.\nIt never forgives a mistake."),
    "MISMAGIUS": dict(prevo="MISDREAVUS", evo="EVO_ITEM, ITEM_DUSK_STONE", realnum=429, text="Its cries sound like incantations.\nThose hearing it are tormented by\nheadaches and hallucinations."),
    "AMBIPOM": dict(prevo="AIPOM", evo="EVO_MOVE, MOVE_DOUBLE_HIT", realnum=424, text="Its split tails are so adept at handling\nthings that AMBIPOM now rarely uses\nits hands."),
    "ROSERADE": dict(prevo="ROSELIA", evo="EVO_ITEM, ITEM_SHINY_STONE", realnum=407, text="With the movements of a dancer, it\nstrikes with whips that are densely\nlined with poison thorns."),
    # Twin Beam and Hyper Drill aren't in the game: level 32, where they learn them
    "FARIGIRAF": dict(prevo="GIRAFARIG", evo="EVO_LEVEL, 32", realnum=981, text="Now that the brain waves from its head\nand tail are in sync, its psychic\npower is ten times stronger."),
    "DUDUNSPARCE": dict(prevo="DUNSPARCE", evo="EVO_LEVEL, 32", realnum=982, name="DUDUNSPRCE", exp="DUDUNSPARCE_TWO_SEGMENT", text="It uses its hard tail to make its nest\nby boring holes into bedrock deep\nunderground."),
    # typing changes
    "PROBOPASS": dict(prevo="NOSEPASS", evo="EVO_ITEM, ITEM_THUNDER_STONE", realnum=476,
                      text="It freely controls three small units\ncalled MINI-NOSES using magnetic force.\nIt is surrounded by a strong field."),
    "WYRDEER": dict(prevo="STANTLER", evo="EVO_MOVE, MOVE_ZEN_HEADBUTT", realnum=899,
                    text="The black orbs on its antlers shine with\nan eerie light. It creates a barrier\nwith psychic power."),
    "URSALUNA": dict(prevo="URSARING", evo="EVO_ITEM, ITEM_PEAT_BLOCK", realnum=901,
                     text="Swampy terrain gave it its brawn. It can\nsense the earth and dig up peat with\nits bare forelegs."),
    "ANNIHILAPE": dict(prevo="PRIMEAPE", evo="EVO_LEVEL, 35", realnum=979,
                       text="When its anger rose beyond a critical\npoint, it gained power unfettered by\nits physical body."),
    # branch evolutions
    "GALLADE": dict(prevo="KIRLIA", evo="EVO_ITEM_MALE, ITEM_DAWN_STONE", realnum=475,
                    text="A master of courtesy and swordsmanship,\nit fights using extending swords on its\nelbows."),
    "FROSLASS": dict(prevo="SNORUNT", evo="EVO_ITEM_FEMALE, ITEM_DAWN_STONE", realnum=478,
                     text="It freezes foes with an icy breath\nnearly -60 degrees F. What seems to be\nits body is actually hollow."),
    "LEAFEON": dict(prevo="EEVEE", evo="EVO_ITEM, ITEM_LEAF_STONE", realnum=470,
                    text="Just like a plant, it uses\nphotosynthesis. As a result, it is\nalways enveloped in clear air."),
    "GLACEON": dict(prevo="EEVEE", evo="EVO_ITEM, ITEM_ICE_STONE", realnum=471,
                    text="As a protective technique, it can\ncompletely freeze its fur to make its\nhairs stand up like needles."),
    "SYLVEON": dict(prevo="EEVEE", evo="EVO_MOVE_TYPE, TYPE_FAIRY", realnum=700,
                    text="It sends a soothing aura from its\nribbonlike feelers to calm fights."),
    "KLEAVOR": dict(prevo="SCYTHER", evo="EVO_ITEM, ITEM_BLACK_AUGURITE", realnum=900,
                    text="Its axes are made of stone. It hews\nlarge trees with them and is said to\nbe a wild, aggressive POKéMON."),
}
S = dict(NEW_SPECIES[NAME])
sdkey = NAME.lower().replace("_", "")
Title = NAME.title().replace("_", "")
S["evo"] = "{%s, SPECIES_%s}" % (S["evo"], NAME)


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


if f"#define SPECIES_{NAME} " in read("include/constants/species.h"):
    sys.exit(f"{NAME} is already in the game")

# free slots: species slots E..Z and internal National Dex numbers after Deoxys
spec_h, dex_h = read("include/constants/species.h"), read("include/constants/pokedex.h")
used = set(re.findall(r"SPECIES_(OLD_UNOWN_[A-Z]+)\b", spec_h.split("#define SPECIES_OLD_UNOWN_Z")[1]))
S["slot"] = next((f"OLD_UNOWN_{c}" for c in "EFGHIJKLMNOPQRSTUVWXYZ" if f"OLD_UNOWN_{c}" not in used), None)
# once the placeholder slots are used up, new species go after Chimecho and the Egg (= NUM_SPECIES) moves up
APPEND = S["slot"] is None
if APPEND:
    S["id"] = int(re.search(r"#define SPECIES_EGG (\d+)", spec_h).group(1))
dused = set(re.findall(r"#define NATIONAL_DEX_\w+ NATIONAL_DEX_(OLD_UNOWN_[A-Z])", dex_h))
S["dexslot"] = next((f"OLD_UNOWN_{c}" for c in "BCDEFGHIJKLMNOPQRSTUVWXYZ" if f"OLD_UNOWN_{c}" not in dused), None)
# internal National Dex numbers: 387-411 (old Unown placeholders), then 412 on
def dexvalue(rhs):
    m = re.match(r"NATIONAL_DEX_OLD_UNOWN_([A-Z])$", rhs)
    return 387 + "BCDEFGHIJKLMNOPQRSTUVWXYZ".index(m.group(1)) if m else int(rhs)
dex_aliases = re.findall(r"#define NATIONAL_DEX_(\w+) (NATIONAL_DEX_OLD_UNOWN_[A-Z]|\d+)\n", dex_h)
if S["dexslot"] is None:
    S["dexslot"] = str(max(dexvalue(v) for _, v in dex_aliases) + 1)

# the expansion's species entry: Pokedex data, sprite positions, breeding data
import glob
xsrc = "".join(read(f) for f in sorted(glob.glob(os.path.join(EXP, "src/data/pokemon/species_info/gen_*_families.h"))))
xb = re.search(r"\[SPECIES_%s\] =\n    \{(.*?)\n    \}," % S.get("exp", NAME), xsrc, re.S).group(1)
def xf(k, default=None):
    m = re.search(r"\.%s\s*=\s*(.*?),\n" % k, xb)
    return m.group(1).strip() if m else default
def coords(k):
    w, h = re.search(r"MON_COORDS_SIZE\((\d+), (\d+)\)", xf(k)).groups()
    return int(w), int(h)
desc = " ".join(re.findall(r'"(.*?)"', re.search(r"\.description = COMPOUND_STRING\((.*?)\),\n", xb, re.S).group(1)))
desc = re.sub(r"\\n", " ", desc)
sentences = re.findall(r"[^.!?]+[.!?]", desc)
while len(textwrap.wrap(" ".join(sentences), 40)) > 3 and len(sentences) > 1:
    sentences.pop()
S.setdefault("text", "\n".join(textwrap.wrap(" ".join(sentences).strip(), 40)[:3]))
S["category"] = re.sub(r'_\("(.*)"\)', r"\1", xf("categoryName")).upper()
S["height"], S["weight"] = int(xf("height")), int(xf("weight"))
S["scale"] = tuple(int(xf(k)) for k in ("pokemonScale", "pokemonOffset", "trainerScale", "trainerOffset"))
S["front"] = coords("frontPicSize") + (int(xf("frontPicYOffset")),)
S["back"] = coords("backPicSize") + (int(xf("backPicYOffset")),)
S["iconpal"] = int(xf("iconPalIndex"))
assert S["iconpal"] <= 2, "FireRed has three icon palettes"
S["bodycolor"] = xf("bodyColor")
S["expyield"] = min(255, int(re.findall(r"\d+", xf("expYield"))[-1]))
S["catchrate"] = int(xf("catchRate"))
items_h = read("include/constants/items.h")
fr_item = lambda it: it if it and re.search(r"#define %s " % it, items_h) else "ITEM_NONE"
S["itemcommon"], S["itemrare"] = fr_item(xf("itemCommon")), fr_item(xf("itemRare"))
S["evs"] = {k: int(xf("evYield_" + k, "0")) for k in ("HP", "Attack", "Defense", "Speed", "SpAttack", "SpDefense")}

dex = ts_entry(SD + "/pokedex.ts", sdkey)
stats = dict(re.findall(r"(hp|atk|def|spa|spd|spe): (\d+)", re.search(r"baseStats: \{(.*?)\}", dex).group(1)))
types = ["TYPE_" + t.upper() for t in re.findall(r'"(\w+)"', re.search(r"types: \[(.*?)\]", dex).group(1))]
types = (types * 2)[:2]
abil = dict(re.findall(r'(\w): "([^"]+)"', re.search(r"abilities: \{(.*?)\}", dex).group(1)))
const = lambda a: "ABILITY_" + re.sub(r"[^A-Z0-9]+", "_", a.upper()).strip("_")
abil_h = read("include/constants/abilities.h")
const = lambda a: (lambda c: c if re.search(r"#define %s " % c, abil_h) else "ABILITY_NONE")("ABILITY_" + re.sub(r"[^A-Z0-9]+", "_", a.upper()).strip("_"))
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
if APPEND:
    edit("include/constants/species.h", f"#define SPECIES_EGG {S['id']}",
         f"#define {SP} {S['id']} // FireRed QoL+Hard: new species (tools/hack/add_species.py)\n#define SPECIES_EGG {S['id'] + 1}")
else:
    edit("include/constants/species.h", "#define IS_DEOXYS_FORME(species)",
         f"#define {SP} SPECIES_{S['slot']} // FireRed QoL+Hard: new species (tools/hack/add_species.py)\n#define IS_DEOXYS_FORME(species)")
DEXRHS = f"NATIONAL_DEX_{S['dexslot']}" if not S["dexslot"].isdigit() else S["dexslot"]
edit("include/constants/pokedex.h", "#define NATIONAL_DEX_COUNT  ",
     f"#define NATIONAL_DEX_{NAME} {DEXRHS}\n#define NATIONAL_DEX_COUNT  ")
s = read("include/constants/pokedex.h")
aliases = re.findall(r"#define NATIONAL_DEX_(\w+) (NATIONAL_DEX_OLD_UNOWN_[A-Z]|\d+)\n", s)
top_name = max(aliases, key=lambda a: dexvalue(a[1]))[0]
s = re.sub(r"#define NATIONAL_DEX_COUNT  NATIONAL_DEX_\w+", f"#define NATIONAL_DEX_COUNT  NATIONAL_DEX_{top_name}", s)
write("include/constants/pokedex.h", s)
if APPEND:
    # positional species -> Hoenn / National tables: append after the last entry (no Hoenn number)
    t = read("src/pokemon.c")
    for table, val in (("sSpeciesToHoennPokedexNum", "0"), ("sSpeciesToNationalPokedexNum", f"NATIONAL_DEX_{NAME}")):
        a = t.index(f"static const u16 {table}[NUM_SPECIES - 1] =")
        b = t.index("};", a)
        t = t[:b] + f"    {val}, // {NAME}\n" + t[b:]
    write("src/pokemon.c", t)
else:
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
        .catchRate = {S['catchrate']},
        .expYield = {S['expyield']},
        .evYield_HP = {S['evs']['HP']},
        .evYield_Attack = {S['evs']['Attack']},
        .evYield_Defense = {S['evs']['Defense']},
        .evYield_Speed = {S['evs']['Speed']},
        .evYield_SpAttack = {S['evs']['SpAttack']},
        .evYield_SpDefense = {S['evs']['SpDefense']},
        .itemCommon = {S['itemcommon']},
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
# single-gender evolutions (Gallade, Froslass) keep their own gender ratio
if xf("genderRatio") in ("MON_MALE", "MON_FEMALE", "MON_GENDERLESS"):
    info = re.sub(r"\.genderRatio = .*?,\n", f".genderRatio = {xf('genderRatio')},\n", info)
if APPEND:
    k = s.rstrip().rindex("};")
    s = s[:k].rstrip() + "\n\n    " + info + ",\n" + s[k:]
else:
    s = s.replace(f"[SPECIES_{S['slot']}] = OLD_UNOWN_SPECIES_INFO", info, 1)
assert f"[{SP}] =" in s
write(p, s)
if APPEND:
    t = read("src/data/text/species_names.h")
    k = t.rstrip().rindex("};")
    write("src/data/text/species_names.h", t[:k].rstrip() + f'\n    [{SP}] = _("{S.get("name", NAME)}"),\n' + t[k:])
else:
    edit("src/data/text/species_names.h", f'    [SPECIES_{S["slot"]}] = _("?"),', f'    [{SP}] = _("{S.get("name", NAME)}"),')

# ---------------------------------------------------------------- graphics
src = os.path.join(EXP, "graphics/pokemon", NAME.lower())
dst = os.path.join("graphics/pokemon", NAME.lower())
os.makedirs(dst, exist_ok=True)
front = Image.open(os.path.join(src, "anim_front.png") if os.path.exists(os.path.join(src, "anim_front.png")) else os.path.join(src, "front.png"))
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
def gfx(f, placeholder, line, egg_anchor):
    if APPEND:
        edit(g + f, egg_anchor, line + egg_anchor)
    else:
        edit(g + f, placeholder, line.strip().rstrip(","))
gfx("front_pic_table.h", f"SPECIES_SPRITE({S['slot']}, gMonFrontPic_DoubleQuestionMark)", f"SPECIES_SPRITE({NAME}, gMonFrontPic_{Title}),\n    ", "SPECIES_SPRITE(EGG,")
gfx("back_pic_table.h", f"SPECIES_SPRITE({S['slot']}, gMonBackPic_DoubleQuestionMark)", f"SPECIES_SPRITE({NAME}, gMonBackPic_{Title}),\n    ", "SPECIES_SPRITE(EGG,")
gfx("palette_table.h", f"SPECIES_PAL({S['slot']}, gMonPalette_DoubleQuestionMark)", f"SPECIES_PAL({NAME}, gMonPalette_{Title}),\n    ", "SPECIES_PAL(EGG,")
gfx("shiny_palette_table.h", f"SPECIES_SHINY_PAL({S['slot']}, gMonShinyPalette_DoubleQuestionMark)", f"SPECIES_SHINY_PAL({NAME}, gMonShinyPalette_{Title}),\n    ", "SPECIES_SHINY_PAL(EGG,")
gfx("footprint_table.h", f"[SPECIES_{S['slot']}] = gMonFootprint_QuestionMark", f"[{SP}] = gMonFootprint_{Title},\n    ", "[SPECIES_EGG] = gMonFootprint")
for f, (w, h, y) in (("front_pic_coordinates.h", S["front"]), ("back_pic_coordinates.h", S["back"])):
    s = read(g + f)
    if APPEND:
        s, n = s.replace("    [SPECIES_EGG] =\n", f"    [{SP}] =\n    {{\n        .size = MON_COORDS_SIZE({w}, {h}),\n        .y_offset = {y},\n    }},\n    [SPECIES_EGG] =\n", 1), 1
    else:
        s, n = re.subn(r"\[SPECIES_%s\] =\n    \{\n        \.size = MON_COORDS_SIZE\(\d+, \d+\),\n        \.y_offset = \d+," % S["slot"],
                       f"[{SP}] =\n    {{\n        .size = MON_COORDS_SIZE({w}, {h}),\n        .y_offset = {y},", s)
    assert n == 1, f
    write(g + f, s)
if APPEND:
    edit("src/pokemon_icon.c", "    [SPECIES_EGG]         = gMonIcon_Egg,", f"    [{SP}] = gMonIcon_{Title},\n    [SPECIES_EGG]         = gMonIcon_Egg,")
    edit("src/pokemon_icon.c", "    [SPECIES_EGG]         = 1,", f"    [{SP}] = {S['iconpal']},\n    [SPECIES_EGG]         = 1,")
else:
    edit("src/pokemon_icon.c", f"    [SPECIES_{S['slot']}] = gMonIcon_QuestionMark,", f"    [{SP}] = gMonIcon_{Title},")
    edit("src/pokemon_icon.c", f"    [SPECIES_{S['slot']}] = 0,", f"    [{SP}] = {S['iconpal']},")
row = re.search(r"\[SPECIES_%s\s*- 1\] = (\{[^}]*\})," % prevo, read("src/menu2.c")).group(1)
s = read("src/menu2.c")
if APPEND:
    s, n = re.subn(r"(    \[SPECIES_CHIMECHO\s*- 1\] = \{[^}]*\},\n)", lambda m: m.group(1) + f"    [{SP} - 1] = {row},\n", s)
else:
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
if APPEND:
    t = read("src/data/pokemon/cry_ids.h")
    k = t.rstrip().rindex("};")
    write("src/data/pokemon/cry_ids.h", t[:k].rstrip() + f"\n    [{SP} - HOENN_MON_SPECIES_START] = CRY_{NAME},\n" + t[k:])
else:
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
newarr = (f"static const u16 s{Title}LevelUpLearnset[] = {{\n" +
          "".join(f"    LEVEL_UP_MOVE({lv:2d}, {mv}),\n" for lv, mv in lu2) + "    LEVEL_UP_END\n};")
if APPEND:
    s = s.rstrip("\n") + "\n\n" + newarr + "\n"
    write(p, s)
    t = read("src/data/pokemon/level_up_learnset_pointers.h")
    k = t.rstrip().rindex("};")
    write("src/data/pokemon/level_up_learnset_pointers.h", t[:k].rstrip() + f"\n    [{SP}] = s{Title}LevelUpLearnset,\n" + t[k:])
else:
    slotnum = re.search(r"#define SPECIES_%s (\d+)" % S["slot"], read("include/constants/species.h")).group(1)
    old = re.search(r"static const u16 sSpecies%sLevelUpLearnset\[\] = \{.*?\};" % slotnum, s, re.S).group(0)
    s = s.replace(old, newarr)
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
if APPEND:
    k = s.rstrip().rindex("};")
    s = s[:k].rstrip() + f"\n\n    [{SP}] = TMHM_LEARNSET({body}),\n" + s[k:]
else:
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
m = re.search(r"    \[SPECIES_%s\]\s*= \{\{.*?\}\},\n" % prevo, s, re.S)
if m:
    s = s.replace(m.group(0), m.group(0)[:-4] + "}, " + S["evo"] + "},\n")
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
names[nat] = S.get("name", NAME)


def list_body(label):
    i = s.index(f"const u16 {label}[] =")
    a = s.index("{", i) + 1
    b = s.index("};", a)
    return a, b


a, b = list_body("gPokedexOrder_Alphabetical")
items = [x.strip() for x in s[a:b].split(",") if x.strip()]
if not S["dexslot"].isdigit():
    items.remove(f"NATIONAL_DEX_{S['dexslot']}")
pos = next(i for i, x in enumerate(items) if x in names and names[x] > S.get("name", NAME) and not x.startswith("NATIONAL_DEX_OLD"))
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
if not APPEND:
    items.remove(f"SPECIES_{S['slot']}")
items.insert(items.index(f"SPECIES_{prevo}") + 1, SP)
s = s[:a] + "\n" + ",\n".join("    " + x for x in items) + "\n" + s[b:]
write(p, s)

# habitat: next to the pre-evolution, or on a new page right after a full one
s = read("src/data/pokemon/pokedex_categories.h")
pages = re.findall(r"static const u16 (sDexCategory_\w+)\[\] = \{(.*?)\};", s, re.S)
page = next(n for n, b in pages if f"SPECIES_{prevo}," in b)
cands = [n for n, b in pages if n == page or n.startswith(page + "_Hack")]
dest = next((n for n in cands if dict(pages)[n].count("SPECIES_") < 4), None)
if dest is None:
    dest = f"{page}_Hack{len(cands)}"
    prev = cands[-1]
    i = s.index(f"static const u16 {prev}[] = {{")
    i = s.index("};\n", i) + 3
    s = s[:i] + f"\nstatic const u16 {dest}[] = {{\n    {SP},\n}};\n" + s[i:]
    short = prev.replace("sDexCategory_", "")
    s = s.replace(f"    DEX_CATEGORY({short}),\n", f"    DEX_CATEGORY({short}),\n    DEX_CATEGORY({dest.replace('sDexCategory_', '')}),\n", 1)
else:
    i = s.index(f"static const u16 {dest}[] = {{")
    j = s.index("};", i)
    blk = s[i:j]
    if f"    SPECIES_{prevo},\n" in blk:
        blk = blk.replace(f"    SPECIES_{prevo},\n", f"    SPECIES_{prevo},\n    {SP},\n")
    else:
        blk = blk.rstrip() + f"\n    {SP},\n"
    s = s[:i] + blk + s[j:]
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

# ---------------------------------------------------------------- engine support (first run only)
# "Level up knowing a move" evolutions (Mamoswine, Ambipom...)
if "EVO_MOVE" not in read("include/constants/pokemon.h"):
    edit("include/constants/pokemon.h", "#define EVO_BEAUTY           15 // Pokémon levels up with beauty ≥ specified value\n",
         "#define EVO_BEAUTY           15 // Pokémon levels up with beauty ≥ specified value\n"
         "#define EVO_MOVE             16 // FireRed QoL+Hard: Pokémon levels up knowing the specified move\n")
    edit("src/pokemon.c", """            case EVO_BEAUTY:
                if (gEvolutionTable[species][i].param <= beauty)
                    targetSpecies = gEvolutionTable[species][i].targetSpecies;
                break;
            }""", """            case EVO_BEAUTY:
                if (gEvolutionTable[species][i].param <= beauty)
                    targetSpecies = gEvolutionTable[species][i].targetSpecies;
                break;
            case EVO_MOVE:
                {
                    u8 j;
                    for (j = 0; j < MAX_MON_MOVES; j++)
                        if (GetMonData(mon, MON_DATA_MOVE1 + j, NULL) == gEvolutionTable[species][i].param)
                            targetSpecies = gEvolutionTable[species][i].targetSpecies;
                }
                break;
            }""")
# Gender-specific item evolutions (Gallade, Froslass), Fairy-move evolutions (Sylveon), 8 evolutions per Pokemon (Eevee)
if "EVO_ITEM_MALE" not in read("include/constants/pokemon.h"):
    edit("include/constants/pokemon.h", "#define EVO_MOVE             16 // FireRed QoL+Hard: Pokémon levels up knowing the specified move\n",
         "#define EVO_MOVE             16 // FireRed QoL+Hard: Pokémon levels up knowing the specified move\n"
         "#define EVO_ITEM_MALE        17 // FireRed QoL+Hard: specified item is used on a male Pokémon\n"
         "#define EVO_ITEM_FEMALE      18 // FireRed QoL+Hard: specified item is used on a female Pokémon\n"
         "#define EVO_MOVE_TYPE        19 // FireRed QoL+Hard: levels up with friendship ≥ 220 knowing a move of the specified type\n")
    edit("include/constants/pokemon.h", "#define EVOS_PER_MON 5", "#define EVOS_PER_MON 8")
    edit("src/pokemon.c", """            case EVO_MOVE:
                {""", """            case EVO_MOVE_TYPE:
                {
                    u8 j;
                    if (friendship >= 220)
                        for (j = 0; j < MAX_MON_MOVES; j++)
                            if (gBattleMoves[GetMonData(mon, MON_DATA_MOVE1 + j, NULL)].type == gEvolutionTable[species][i].param
                             && GetMonData(mon, MON_DATA_MOVE1 + j, NULL) != MOVE_NONE)
                                targetSpecies = gEvolutionTable[species][i].targetSpecies;
                }
                break;
            case EVO_MOVE:
                {""")
    edit("src/pokemon.c", """            if (gEvolutionTable[species][i].method == EVO_ITEM
             && gEvolutionTable[species][i].param == evolutionItem)
            {""", """            if (gEvolutionTable[species][i].param == evolutionItem
             && (gEvolutionTable[species][i].method == EVO_ITEM
              || (gEvolutionTable[species][i].method == EVO_ITEM_MALE && GetMonGender(mon) == MON_MALE)
              || (gEvolutionTable[species][i].method == EVO_ITEM_FEMALE && GetMonGender(mon) == MON_FEMALE)))
            {""")
# The National Dex list shows Pokemon added after Deoxys in real-number order
if "Hack_NationalOrder" not in read("src/pokemon.c"):
    edit("src/pokemon.c", "u16 SpeciesToPokedexNum(u16 species)\n{", """// i-th row of the National Dex list (0-based) -> internal National Dex number
u16 Hack_NationalOrder(u16 i)
{
    u16 j, k, rank;

    if (i < NATIONAL_DEX_DEOXYS)
        return i + 1;
    i -= NATIONAL_DEX_DEOXYS;
    for (j = 0; j < ARRAY_COUNT(sHackRealDexNums); j++)
    {
        rank = 0;
        for (k = 0; k < ARRAY_COUNT(sHackRealDexNums); k++)
            if (sHackRealDexNums[k] < sHackRealDexNums[j])
                rank++;
        if (rank == i)
            return NATIONAL_DEX_DEOXYS + 1 + j;
    }
    return NATIONAL_DEX_DEOXYS + 1 + i;
}

u16 SpeciesToPokedexNum(u16 species)
{""")
    edit("include/pokemon.h", "u16 Hack_DisplayDexNum(u16 dexNum);", "u16 Hack_DisplayDexNum(u16 dexNum);\nu16 Hack_NationalOrder(u16 i);")
    s = read("src/pokedex_screen.c")
    i = s.index("    case DEX_ORDER_NUMERICAL_NATIONAL:\n        for (i = 0; i < NATIONAL_DEX_COUNT; i++)")
    j = s.index("break;", i)
    blk = s[i:j].replace("            ndex_num = i + 1;", "            ndex_num = Hack_NationalOrder(i);").replace("                ret = ndex_num;", "                ret = i + 1;")
    write("src/pokedex_screen.c", s[:i] + blk + s[j:])

# ---------------------------------------------------------------- evolution items
STONE_DESC = "A peculiar stone that makes certain\\\\nspecies of POKéMON evolve.\\\\n{}"
EVO_ITEMS = {
    "RAZOR_CLAW": dict(slot="ITEM_035", name="RAZOR CLAW", hold="HOLD_EFFECT_SCOPE_LENS",
                       desc="A sharply hooked claw that boosts\\\\nthe holder's critical-hit ratio.\\\\nIt can make SNEASEL evolve."),
    "RAZOR_FANG": dict(slot="ITEM_036", name="RAZOR FANG", hold="HOLD_EFFECT_FLINCH", param=10,
                       desc="A sharp fang that may make the foe\\\\nflinch when the holder attacks.\\\\nIt can make GLIGAR evolve."),
    "DUSK_STONE": dict(slot="ITEM_037", name="DUSK STONE", desc=STONE_DESC.format("It is as dark as dark can be.")),
    "SHINY_STONE": dict(slot="ITEM_038", name="SHINY STONE", desc=STONE_DESC.format("It shines with a dazzling light.")),
    "PROTECTOR": dict(slot="ITEM_039", name="PROTECTOR", desc="A protective item of some sort.\\\\nIt is extremely stiff and heavy.\\\\nIt can make RHYDON evolve."),
    "ELECTIRIZER": dict(slot="ITEM_03A", name="ELECTIRIZER", desc="A box packed with a tremendous\\\\namount of electric energy.\\\\nIt can make ELECTABUZZ evolve."),
    "MAGMARIZER": dict(slot="ITEM_03B", name="MAGMARIZER", desc="A box packed with a tremendous\\\\namount of magma energy.\\\\nIt can make MAGMAR evolve."),
    "DUBIOUS_DISC": dict(slot="ITEM_03C", name="DUBIOUS DISC", desc="A transparent device overflowing\\\\nwith dubious data.\\\\nIt can make PORYGON2 evolve."),
    "REAPER_CLOTH": dict(slot="ITEM_03D", name="REAPER CLOTH", desc="A cloth imbued with horrifyingly\\\\nstrong spiritual energy.\\\\nIt can make DUSCLOPS evolve."),
    "DAWN_STONE": dict(slot="ITEM_03E", name="DAWN STONE", desc=STONE_DESC.format("It sparkles like a glittering eye.")),
    "ICE_STONE": dict(slot="ITEM_048", name="ICE STONE", desc=STONE_DESC.format("It has an unmistakable snowflake.")),
    "PEAT_BLOCK": dict(slot="ITEM_052", name="PEAT BLOCK", desc="A block of muddy material. It\\\\ncan make URSARING evolve when\\\\nused on it."),
    "BLACK_AUGURITE": dict(slot="ITEM_057", name="BLK AUGURITE", desc="A glassy black stone that\\\\nsplits apart when struck.\\\\nIt can make SCYTHER evolve."),
}
for item, I in EVO_ITEMS.items():
    I.setdefault("price", 2100)
    I.setdefault("hold", "HOLD_EFFECT_NONE")
    I.setdefault("param", 0)
    I.setdefault("shop", "CeladonCity_DepartmentStore_4F")
    I.setdefault("after", "ITEM_UP_GRADE")
# (tools/hack/balance.py later moves the held evolution items to the 5-badge list)
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
                     ("holdEffect", f'"{I["hold"]}"'), ("holdEffectParam", str(I["param"])), ("description_english", f'"{I["desc"]}"'),
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
        t = read("src/data/item_icon_table.h")
        t, n = re.subn(r"    \[%s\]\s*= \{gItemIcon_QuestionMark, gItemIconPalette_QuestionMark\}," % I["slot"],
                       f"    [ITEM_{item}] = {{gItemIcon_{T}, gItemIconPalette_{T}}},", t)
        assert n == 1, item
        write("src/data/item_icon_table.h", t)
        edit("src/data/pokemon/item_effects.h", "    [ITEM_UP_GRADE - ITEM_POTION]       = sItemEffect_FireStone, // same effect as every stone\n",
             "    [ITEM_UP_GRADE - ITEM_POTION]       = sItemEffect_FireStone, // same effect as every stone\n"
             f"    [ITEM_{item} - ITEM_POTION]    = sItemEffect_FireStone, // same effect as every stone\n")
        edit(f"data/maps/{I['shop']}/scripts.inc", f"\t.2byte {I['after']}\n", f"\t.2byte {I['after']}\n\t.2byte ITEM_{item}\n")
        print("added item", item)

