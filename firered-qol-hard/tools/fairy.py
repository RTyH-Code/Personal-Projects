#!/usr/bin/env python3
"""Fairy type (Gen 6) for FireRed QoL+Hard.

* TYPE_FAIRY with its modern matchups; Steel no longer resists Ghost and Dark.
* The 18 Gen 1-3 Pokemon that became part Fairy get their modern types.
* Charm, Sweet Kiss and Moonlight become Fairy-type.
* Six Fairy attacks: Fairy Wind, Disarming Voice, Draining Kiss, Dazzling
  Gleam, Play Rough and Moonblast, with animations built from existing ones.
  They're added to level-up learnsets (and egg moves) where modern games
  have them, using the same generation rule as modernize.py.
* A FAIRY type icon, drawn from the existing icon lettering.

Run once from the repo root after the other tools/hack scripts:
    python3 tools/hack/fairy.py <pokemon-showdown>/data
Showdown's data files are read as text, never run.
"""
import re
import sys

from PIL import Image

SD = sys.argv[1]


def read(p):
    return open(p, encoding="utf-8").read()


def write(p, s):
    open(p, "w", encoding="utf-8").write(s)


def edit(p, old, new, count=1):
    s = read(p)
    assert old in s, (p, old)
    write(p, s.replace(old, new, count))


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def ts_entries(path):
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


# ---------------------------------------------------------------- the type
edit("include/constants/pokemon.h", "#define TYPE_DARK           17\n#define NUMBER_OF_MON_TYPES 18",
     "#define TYPE_DARK           17\n#define TYPE_FAIRY          18\n#define NUMBER_OF_MON_TYPES 19")

p = "src/battle_main.c"
s = read(p)
# 336 bytes + 12 Fairy rows - 2 Steel rows = 366 (also declared in battle_main.h)
s = s.replace("const u8 gTypeEffectiveness[336] =", "const u8 gTypeEffectiveness[366] =", 1)
for line in ("    TYPE_GHOST, TYPE_STEEL, TYPE_MUL_NOT_EFFECTIVE,\n", "    TYPE_DARK, TYPE_STEEL, TYPE_MUL_NOT_EFFECTIVE,\n"):
    assert line in s, line
    s = s.replace(line, "", 1)
fairy = [("FAIRY", "FIGHTING", 20), ("FAIRY", "DRAGON", 20), ("FAIRY", "DARK", 20),
         ("FAIRY", "FIRE", 5), ("FAIRY", "POISON", 5), ("FAIRY", "STEEL", 5),
         ("POISON", "FAIRY", 20), ("STEEL", "FAIRY", 20),
         ("FIGHTING", "FAIRY", 5), ("BUG", "FAIRY", 5), ("DARK", "FAIRY", 5), ("DRAGON", "FAIRY", 0)]
mul = {20: "TYPE_MUL_SUPER_EFFECTIVE", 5: "TYPE_MUL_NOT_EFFECTIVE", 0: "TYPE_MUL_NO_EFFECT"}
rows = "".join(f"    TYPE_{a}, TYPE_{d}, {mul[m]},\n" for a, d, m in fairy)
anchor = "    TYPE_FORESIGHT, TYPE_FORESIGHT, TYPE_MUL_NO_EFFECT,\n"
assert anchor in s
s = s.replace(anchor, rows + anchor, 1)
s = s.replace('    [TYPE_DARK] = _("DARK"),\n', '    [TYPE_DARK] = _("DARK"),\n    [TYPE_FAIRY] = _("FAIRY"),\n', 1)
assert '[TYPE_FAIRY] = _("FAIRY")' in s
write(p, s)

edit("include/battle_main.h", "extern const u8 gTypeEffectiveness[336];", "extern const u8 gTypeEffectiveness[366];")

# Hidden Power still picks from Fighting..Dark (16 types), never Fairy.
for p in ("src/battle_script_commands.c", "src/pokemon_summary_screen.c"):
    edit(p, "(NUMBER_OF_MON_TYPES - 3) * typeBits", "15 * typeBits")

edit("src/tm_case.c", "#define NUM_DISC_COLORS ((NUMBER_OF_MON_TYPES - 1) * 16)",
     "#define NUM_DISC_COLORS (17 * 16) // Normal..Dark; there are no Fairy TMs")
edit("src/tm_case.c", "    [TYPE_DRAGON]   = 0x100\n", "    [TYPE_DRAGON]   = 0x100,\n    [TYPE_FAIRY]    = 0x0d0\n")
edit("src/data/union_room.h", "    { gTypeNames[TYPE_DARK],     TYPE_DARK           },\n",
     "    { gTypeNames[TYPE_DARK],     TYPE_DARK           },\n    { gTypeNames[TYPE_FAIRY],    TYPE_FAIRY          },\n")
edit("src/data/union_room.h", "static const struct ListMenuItem sListMenuItems_TypeNames[NUMBER_OF_MON_TYPES] =",
     "static const struct ListMenuItem sListMenuItems_TypeNames[NUMBER_OF_MON_TYPES + 1] =")
edit("src/data/union_room.h", "    .totalItems = NUMBER_OF_MON_TYPES,", "    .totalItems = NUMBER_OF_MON_TYPES + 1,")
edit("src/battle_message.c", 'const u8 gText_ADarkMove[] = _("a DARK move");',
     'const u8 gText_ADarkMove[] = _("a DARK move");\nconst u8 gText_AFairyMove[] = _("a FAIRY move");')
edit("src/battle_message.c", "    [TYPE_DARK]     = gText_ADarkMove\n",
     "    [TYPE_DARK]     = gText_ADarkMove,\n    [TYPE_FAIRY]    = gText_AFairyMove\n")
edit("src/list_menu.c", "    [TYPE_DARK + 1]     = { 32, 12, 0x8C },\n",
     "    [TYPE_DARK + 1]     = { 32, 12, 0x8C },\n    [TYPE_FAIRY + 1]    = { 32, 12, 0x04 },\n")

# ---------------------------------------------------------------- icon
# Palette slot 10 of pokemon_types.pal (sheet index 26) is unused: make it Fairy pink.
p = "graphics/interface/pokemon_types.pal"
pal = read(p).split("\n")
assert pal[3 + 10].strip() == "222 222 197", pal[3 + 10]
pal[3 + 10] = "238 153 172"
write(p, "\n".join(pal))

im = Image.open("graphics/interface/menu_info.png")
px = im.load()
WHITE, SHADOW, BODY, PINK = 31, 30, 28, 26


def tile_xy(off):
    return (off % 16) * 8, (off // 16) * 8


def glyph(off, c0, c1):
    """Letter pixels (white + shadow) from an icon's columns c0..c1, rows 2-9."""
    ox, oy = tile_xy(off)
    return [[px[ox + c, oy + r] if px[ox + c, oy + r] in (WHITE, SHADOW) else None
             for c in range(c0, c1 + 1)] for r in range(2, 10)]


letters = [glyph(0x24, 7, 11),   # F (FIRE)
           glyph(0xA0, 11, 15),  # A (DRAGON)
           glyph(0x24, 12, 15),  # I (FIRE)
           glyph(0x24, 16, 20),  # R (FIRE)
           glyph(0x60, 12, 15)]  # Y (FLYING)
sx, sy = tile_xy(0x84)            # PSYCHC icon as the base shape
dx, dy = tile_xy(0x04)            # free tiles in the top row
for y in range(12):
    for x in range(32):
        v = px[sx + x, sy + y]
        px[dx + x, dy + y] = 0 if v == 0 else PINK
width = sum(len(g[0]) for g in letters)
x0 = (32 - width) // 2 + 1
for g in letters:
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if v is not None:
                px[dx + x0 + c, dy + 2 + r] = v
    x0 += len(g[0])
im.save("graphics/interface/menu_info.png")

# ---------------------------------------------------------------- species types
FAIRY_MONS = {}
for key, body in ts_entries(SD + "/pokedex.ts"):
    t = "\n".join(body)
    num = re.search(r"num: (\d+)", t)
    if not num or not 1 <= int(num.group(1)) <= 386 or "forme:" in t:
        continue
    types = re.findall(r'"(\w+)"', re.search(r"types: \[(.*?)\]", t).group(1))
    if "Fairy" in types:
        FAIRY_MONS[key] = types
p = "src/data/pokemon/species_info.h"
s = read(p)
names = {norm(c): c for c in re.findall(r"\[(SPECIES_\w+)\] =\n", s)}
for key, types in FAIRY_MONS.items():
    sp = names["species" + key]
    tt = ["TYPE_" + t.upper() for t in types] * (2 if len(types) == 1 else 1)
    s, n = re.subn(r"(\[%s\] =\n    \{.*?\.types = )\{[^}]*\}" % sp, r"\1{%s, %s}" % (tt[0], tt[1]), s, count=1, flags=re.S)
    assert n == 1, sp
write(p, s)
print(f"{len(FAIRY_MONS)} Pokemon retyped")

# ---------------------------------------------------------------- moves
p = "src/data/battle_moves.h"
s = read(p)
for mv in ("MOVE_CHARM", "MOVE_SWEET_KISS", "MOVE_MOONLIGHT"):
    s, n = re.subn(r"(\[%s\] =\s*\{.*?\.type = )TYPE_\w+" % mv, r"\1TYPE_FAIRY", s, count=1, flags=re.S)
    assert n == 1, mv
write(p, s)

NEW = [  # constant, name (12 chars max), effect, power, acc, pp, chance, target, flags, split, description
    ("FAIRY_WIND", "FAIRY WIND", "EFFECT_HIT", 40, 100, 30, 0, "MOVE_TARGET_SELECTED",
     "FLAG_PROTECT_AFFECTED | FLAG_MIRROR_MOVE_AFFECTED | FLAG_KINGS_ROCK_AFFECTED", "SPLIT_SPECIAL",
     "The user stirs up a\\nfairy wind and\\nstrikes the foe\\nwith it."),
    ("DISARMING_VOICE", "DISRMNGVOICE", "EFFECT_ALWAYS_HIT", 40, 0, 15, 0, "MOVE_TARGET_BOTH",
     "FLAG_PROTECT_AFFECTED | FLAG_MIRROR_MOVE_AFFECTED", "SPLIT_SPECIAL",
     "A charming cry that\\nhurts all foes.\\nIt never misses."),
    ("DRAINING_KISS", "DRAININGKISS", "EFFECT_ABSORB", 50, 100, 10, 0, "MOVE_TARGET_SELECTED",
     "FLAG_MAKES_CONTACT | FLAG_PROTECT_AFFECTED | FLAG_MIRROR_MOVE_AFFECTED", "SPLIT_SPECIAL",
     "A kiss that drains\\nHP. The user\\nrestores 3/4 of\\nthe damage dealt."),
    ("DAZZLING_GLEAM", "DAZZLNGGLEAM", "EFFECT_HIT", 80, 100, 10, 0, "MOVE_TARGET_BOTH",
     "FLAG_PROTECT_AFFECTED | FLAG_MIRROR_MOVE_AFFECTED", "SPLIT_SPECIAL",
     "A powerful flash of\\nlight that damages\\nall foes."),
    ("PLAY_ROUGH", "PLAY ROUGH", "EFFECT_ATTACK_DOWN_HIT", 90, 90, 10, 10, "MOVE_TARGET_SELECTED",
     "FLAG_MAKES_CONTACT | FLAG_PROTECT_AFFECTED | FLAG_MIRROR_MOVE_AFFECTED", "SPLIT_PHYSICAL",
     "The user plays\\nrough with the foe.\\nIt may lower the\\nfoe's ATTACK."),
    ("MOONBLAST", "MOONBLAST", "EFFECT_SPECIAL_ATTACK_DOWN_HIT", 95, 100, 15, 30, "MOVE_TARGET_SELECTED",
     "FLAG_PROTECT_AFFECTED | FLAG_MIRROR_MOVE_AFFECTED", "SPLIT_SPECIAL",
     "The power of the\\nmoon attacks the\\nfoe. It may lower\\nSP. ATK."),
]

p = "include/constants/moves.h"
s = read(p)
m = re.search(r"#define MOVE_PSYCHO_BOOST (\d+)\n", s)
first = int(m.group(1)) + 1
defs = "".join(f"#define MOVE_{c} {first + i}\n" for i, (c, *_) in enumerate(NEW))
s = s.replace(m.group(0), m.group(0) + "\n// FireRed QoL+Hard: Fairy moves (tools/hack/fairy.py)\n" + defs, 1)
s, n = re.subn(r"#define MOVES_COUNT \d+", "#define MOVES_COUNT %d" % (first + len(NEW)), s)
assert n == 1
write(p, s)

p = "src/data/battle_moves.h"
s = read(p).rstrip()
assert s.endswith("};")
blocks = ""
for c, name, eff, pw, acc, pp, ch, tgt, fl, split, desc in NEW:
    blocks += f"""
    [MOVE_{c}] =
    {{
        .effect = {eff},
        .power = {pw},
        .type = TYPE_FAIRY,
        .accuracy = {acc},
        .pp = {pp},
        .secondaryEffectChance = {ch},
        .target = {tgt},
        .priority = 0,
        .flags = {fl},
        .split = {split},
    }},
"""
write(p, s[:-2].rstrip() + "\n" + blocks + "};\n")

p = "src/data/text/move_names.h"
s = read(p).rstrip()
assert s.endswith("};")
s = s[:-2].rstrip().rstrip(",") + ",\n" + "".join(f'    [MOVE_{c}] = _("{name}"),\n' for c, name, *_ in NEW) + "};\n"
write(p, s)

p = "src/move_descriptions.c"
s = read(p)
descs = "".join(f'const u8 gMoveDescription_{c.title().replace("_", "")}[] = _("{d}");\n' for c, *_, d in NEW)
s = s.replace("const u8 *const gMoveDescriptionPointers[MOVES_COUNT - 1] = {", descs + "\nconst u8 *const gMoveDescriptionPointers[MOVES_COUNT - 1] = {", 1)
s = s.rstrip()
assert s.endswith("};")
s = s[:-2].rstrip() + "\n" + "".join(f'    [MOVE_{c} - 1] = gMoveDescription_{c.title().replace("_", "")},\n' for c, *_ in NEW) + "};\n"
write(p, s)

# Draining Kiss heals 3/4 of the damage instead of 1/2.
edit("src/battle_script_commands.c", "    gBattleMoveDamage = -(gHpDealt / 2);",
     "    if (gCurrentMove == MOVE_DRAINING_KISS)\n        gBattleMoveDamage = -(gHpDealt * 3 / 4);\n    else\n        gBattleMoveDamage = -(gHpDealt / 2);")
# Disarming Voice is a sound move (blocked by Soundproof).
edit("src/battle_util.c", "static const u16 sSoundMovesTable[] =\n{\n", "static const u16 sSoundMovesTable[] =\n{\n    MOVE_DISARMING_VOICE,\n")

# ---------------------------------------------------------------- animations
PINK = "RGB(31, 19, 24)"
ANIMS = {
    "FAIRY_WIND": f"""Move_FAIRY_WIND:
	loadspritegfx ANIM_TAG_GUST
	loadspritegfx ANIM_TAG_IMPACT
	monbg ANIM_DEF_PARTNER
	splitbgprio ANIM_TARGET
	setalpha 12, 8
	createsprite gSimplePaletteBlendSpriteTemplate, ANIM_ATTACKER, 2, F_PAL_BG, 1, 0, 6, {PINK}
	playsewithpan SE_M_GUST, SOUND_PAN_TARGET
	createsprite gEllipticalGustSpriteTemplate, ANIM_ATTACKER, 2, 0, -16
	createvisualtask AnimTask_AnimateGustTornadoPalette, 5, 1, 70
	waitforvisualfinish
	createvisualtask AnimTask_ShakeMon2, 5, ANIM_TARGET, 1, 0, 7, 1
	createsprite gBasicHitSplatSpriteTemplate, ANIM_ATTACKER, 2, 0, 0, ANIM_TARGET, 2
	playsewithpan SE_M_GUST2, SOUND_PAN_TARGET
	waitforvisualfinish
	createsprite gSimplePaletteBlendSpriteTemplate, ANIM_ATTACKER, 2, F_PAL_BG, 1, 6, 0, {PINK}
	waitforvisualfinish
	clearmonbg ANIM_DEF_PARTNER
	blendoff
	end
""",
    "DISARMING_VOICE": f"""Move_DISARMING_VOICE:
	loadspritegfx ANIM_TAG_THIN_RING
	loadspritegfx ANIM_TAG_RED_HEART
	createvisualtask SoundTask_PlayCryWithEcho, 5
	createsprite gSimplePaletteBlendSpriteTemplate, ANIM_ATTACKER, 2, F_PAL_BG | F_PAL_BATTLERS, 3, 8, 0, {PINK}
	createvisualtask AnimTask_ScaleMonAndRestore, 5, -5, -5, 5, ANIM_ATTACKER, 0
	createsprite gHyperVoiceRingSpriteTemplate, ANIM_ATTACKER, 0, 45, 0, 0, 0, 0, 0, 1
	createvisualtask AnimTask_ShakeMon2, 2, ANIM_TARGET, 1, 0, 6, 1
	createvisualtask AnimTask_ShakeMon2, 2, ANIM_DEF_PARTNER, 1, 0, 6, 1
	createvisualtask SoundTask_WaitForCry, 5
	waitforvisualfinish
	playsewithpan SE_M_ATTRACT, SOUND_PAN_TARGET
	createsprite gRedHeartBurstSpriteTemplate, ANIM_TARGET, 3, 160, -30
	createsprite gRedHeartBurstSpriteTemplate, ANIM_TARGET, 3, -256, -42
	createsprite gRedHeartBurstSpriteTemplate, ANIM_TARGET, 3, 128, -14
	createsprite gRedHeartBurstSpriteTemplate, ANIM_TARGET, 3, -128, -22
	waitforvisualfinish
	end
""",
    "DRAINING_KISS": f"""Move_DRAINING_KISS:
	loadspritegfx ANIM_TAG_RED_HEART
	loadspritegfx ANIM_TAG_ORBS
	loadspritegfx ANIM_TAG_BLUE_STAR
	monbg ANIM_DEF_PARTNER
	splitbgprio_foes ANIM_TARGET
	setalpha 12, 8
	createsprite gSimplePaletteBlendSpriteTemplate, ANIM_ATTACKER, 2, F_PAL_BG, 1, 0, 4, {PINK}
	playsewithpan SE_M_ATTRACT, SOUND_PAN_TARGET
	createsprite gRedHeartBurstSpriteTemplate, ANIM_TARGET, 3, 160, -30
	createsprite gRedHeartBurstSpriteTemplate, ANIM_TARGET, 3, -256, -42
	createsprite gRedHeartBurstSpriteTemplate, ANIM_TARGET, 3, 416, -38
	createvisualtask AnimTask_ShakeMon, 5, ANIM_TARGET, 0, 5, 5, 1
	waitforvisualfinish
	call AbsorbEffect
	waitforvisualfinish
	delay 15
	call HealingEffect
	waitforvisualfinish
	createsprite gSimplePaletteBlendSpriteTemplate, ANIM_ATTACKER, 2, F_PAL_BG, 1, 4, 0, {PINK}
	waitforvisualfinish
	clearmonbg ANIM_DEF_PARTNER
	blendoff
	end
""",
    "DAZZLING_GLEAM": f"""Move_DAZZLING_GLEAM:
	loadspritegfx ANIM_TAG_BLUE_STAR
	playsewithpan SE_M_REFLECT, SOUND_PAN_ATTACKER
	createsprite gSimplePaletteBlendSpriteTemplate, ANIM_ATTACKER, 2, F_PAL_BG | F_PAL_BATTLERS, 1, 0, 12, {PINK}
	waitforvisualfinish
	playsewithpan SE_M_MOONLIGHT, SOUND_PAN_TARGET
	createsprite gHealingBlueStarSpriteTemplate, ANIM_TARGET, 2, -16, -8, 0, 0
	createsprite gHealingBlueStarSpriteTemplate, ANIM_TARGET, 2, 16, 4, 0, 0
	delay 8
	createsprite gHealingBlueStarSpriteTemplate, ANIM_TARGET, 2, 0, -16, 0, 0
	createvisualtask AnimTask_ShakeMon2, 2, ANIM_TARGET, 2, 0, 8, 1
	createvisualtask AnimTask_ShakeMon2, 2, ANIM_DEF_PARTNER, 2, 0, 8, 1
	waitforvisualfinish
	createsprite gSimplePaletteBlendSpriteTemplate, ANIM_ATTACKER, 2, F_PAL_BG | F_PAL_BATTLERS, 1, 12, 0, {PINK}
	waitforvisualfinish
	end
""",
    "PLAY_ROUGH": f"""Move_PLAY_ROUGH:
	loadspritegfx ANIM_TAG_IMPACT
	loadspritegfx ANIM_TAG_RED_HEART
	monbg ANIM_DEF_PARTNER
	setalpha 12, 8
	createsprite gSimplePaletteBlendSpriteTemplate, ANIM_ATTACKER, 2, F_PAL_TARGET, 2, 0, 8, {PINK}
	createvisualtask AnimTask_ShakeMon, 5, ANIM_TARGET, 3, 0, 24, 1
	playsewithpan SE_M_COMET_PUNCH, SOUND_PAN_TARGET
	createsprite gBasicHitSplatSpriteTemplate, ANIM_ATTACKER, 2, -12, -8, ANIM_TARGET, 2
	delay 6
	playsewithpan SE_M_COMET_PUNCH, SOUND_PAN_TARGET
	createsprite gBasicHitSplatSpriteTemplate, ANIM_ATTACKER, 2, 12, 4, ANIM_TARGET, 2
	createsprite gRedHeartBurstSpriteTemplate, ANIM_TARGET, 3, 160, -30
	delay 6
	playsewithpan SE_M_COMET_PUNCH, SOUND_PAN_TARGET
	createsprite gBasicHitSplatSpriteTemplate, ANIM_ATTACKER, 2, -4, 10, ANIM_TARGET, 2
	createsprite gRedHeartBurstSpriteTemplate, ANIM_TARGET, 3, -256, -42
	delay 6
	playsewithpan SE_M_MEGA_KICK2, SOUND_PAN_TARGET
	createsprite gBasicHitSplatSpriteTemplate, ANIM_ATTACKER, 2, 0, 0, ANIM_TARGET, 2
	waitforvisualfinish
	createsprite gSimplePaletteBlendSpriteTemplate, ANIM_ATTACKER, 2, F_PAL_TARGET, 2, 8, 0, {PINK}
	waitforvisualfinish
	clearmonbg ANIM_DEF_PARTNER
	blendoff
	end
""",
    "MOONBLAST": f"""Move_MOONBLAST:
	loadspritegfx ANIM_TAG_MOON
	loadspritegfx ANIM_TAG_GREEN_SPARKLE
	loadspritegfx ANIM_TAG_IMPACT
	setalpha 0, 16
	createsprite gSimplePaletteBlendSpriteTemplate, ANIM_ATTACKER, 2, F_PAL_BG, 1, 0, 16, RGB_BLACK
	waitforvisualfinish
	createsprite gMoonSpriteTemplate, ANIM_ATTACKER, 2, 120, 56
	createvisualtask AnimTask_AlphaFadeIn, 3, 0, 16, 16, 0, 1
	playsewithpan SE_M_MOONLIGHT, 0
	delay 30
	createsprite gMoonlightSparkleSpriteTemplate, ANIM_ATTACKER, 40, -12, 0
	delay 15
	createsprite gMoonlightSparkleSpriteTemplate, ANIM_ATTACKER, 40, 12, 0
	delay 20
	createvisualtask AnimTask_MoonlightEndFade, 2
	waitforvisualfinish
	createsprite gSimplePaletteBlendSpriteTemplate, ANIM_ATTACKER, 2, F_PAL_TARGET, 1, 0, 14, {PINK}
	playsewithpan SE_M_DETECT, SOUND_PAN_TARGET
	createsprite gBasicHitSplatSpriteTemplate, ANIM_ATTACKER, 2, 0, 0, ANIM_TARGET, 1
	createvisualtask AnimTask_ShakeMon2, 2, ANIM_TARGET, 3, 0, 10, 1
	waitforvisualfinish
	createsprite gSimplePaletteBlendSpriteTemplate, ANIM_ATTACKER, 2, F_PAL_TARGET, 1, 14, 0, {PINK}
	waitforvisualfinish
	blendoff
	end
""",
}
p = "data/battle_anim_scripts.s"
s = read(p)
s = s.replace("\t.4byte Move_PSYCHO_BOOST\n", "\t.4byte Move_PSYCHO_BOOST\n" + "".join(f"\t.4byte Move_{c}\n" for c, *_ in NEW), 1)
s = s.replace("@ cannot be reached, because last move is Psycho Boost", "@ cannot be reached", 1)
anchor = "Move_PSYCHO_BOOST:\n"
assert anchor in s
s = s.replace(anchor, "".join(ANIMS[c] + "\n" for c, *_ in NEW) + anchor, 1)
write(p, s)

# ---------------------------------------------------------------- learnsets
sd_num = {}
for key, body in ts_entries(SD + "/moves.ts"):
    m = re.search(r"num: (\d+)", "\n".join(body))
    if m:
        sd_num[key] = int(m.group(1))
NEW_KEYS = {norm(c): "MOVE_" + c for c, *_ in NEW}
learn = {}
for key, body in ts_entries(SD + "/learnsets.ts"):
    moves = {}
    for line in body:
        m = re.match(r"^\t\t\t(\w+): \[(.*)\],?$", line)
        if m:
            moves[m.group(1)] = re.findall(r'"(\d)([LE])(\d*)"', m.group(2))
    learn[key] = moves

ptrs = dict(re.findall(r"\[(SPECIES_\w+)\] = (s\w+LevelUpLearnset)",
                       read("src/data/pokemon/level_up_learnset_pointers.h")))
p = "src/data/pokemon/level_up_learnsets.h"
s = read(p)
added = 0
done = set()
for sp, arr in ptrs.items():
    ls = learn.get(norm(sp[8:]))
    if not ls or arr in done or sp in ("SPECIES_NONE",):
        continue
    gens = {g for entries in ls.values() for g, kind, _ in entries if kind == "L"}
    gen = max((g for g in gens if g in "789"), default=None)
    if gen is None:
        continue
    new = []
    for key, mv in NEW_KEYS.items():
        for g, kind, lvl in ls.get(key, []):
            if g == gen and kind == "L":
                new.append((max(1, int(lvl)), mv))
                break
    if not new:
        continue
    m = re.search(r"static const u16 %s\[\] = \{\n(.*?)    LEVEL_UP_END\n\};" % arr, s, re.S)
    entries = [(int(l), mv) for l, mv in re.findall(r"LEVEL_UP_MOVE\(\s*(\d+),\s*(MOVE_\w+)\)", m.group(1))]
    entries = sorted(entries + new, key=lambda e: e[0])
    assert len(entries) <= 32, arr
    body = "".join(f"    LEVEL_UP_MOVE({l}, {mv}),\n" for l, mv in entries)
    s = s[:m.start(1)] + body + s[m.end(1):]
    added += len(new)
    done.add(arr)
write(p, s)

p = "src/data/pokemon/egg_moves.h"
s = read(p)
egg_added = 0
for sp, body in re.findall(r"egg_moves\((\w+),(.*?)\)", s, re.S):
    ls = learn.get(norm(sp))
    if not ls:
        continue
    have = re.findall(r"MOVE_\w+", body)
    extra = []
    for key, mv in NEW_KEYS.items():
        if any(kind == "E" and g in "789" for g, kind, _ in ls.get(key, [])) and mv not in have:
            extra.append(mv)
    extra = extra[:max(0, 10 - len(have))]
    if extra:
        old = f"egg_moves({sp},{body})"
        new = f"egg_moves({sp},{body.rstrip()},\n              " + ",\n              ".join(extra) + ")"
        s = s.replace(old, new, 1)
        egg_added += len(extra)
write(p, s)
print(f"{added} level-up and {egg_added} egg Fairy moves added")

# ---------------------------------------------------------------- balance
# Lance's Dragons get a Steel move so Fairy Pokemon don't wall him completely.
LANCE = [
    ("sParty_EliteFourLance", "MOVE_HYPER_BEAM, MOVE_SAFEGUARD, MOVE_DRAGON_RAGE, MOVE_OUTRAGE",
     "MOVE_HYPER_BEAM, MOVE_IRON_TAIL, MOVE_DRAGON_RAGE, MOVE_OUTRAGE"),
    ("sParty_EliteFourLance", "MOVE_HYPER_BEAM, MOVE_SAFEGUARD, MOVE_OUTRAGE, MOVE_WING_ATTACK",
     "MOVE_HYPER_BEAM, MOVE_IRON_TAIL, MOVE_OUTRAGE, MOVE_WING_ATTACK"),
    ("sParty_EliteFourLance2", "MOVE_HYPER_BEAM, MOVE_EARTHQUAKE, MOVE_DRAGON_CLAW, MOVE_FLAMETHROWER",
     "MOVE_IRON_TAIL, MOVE_EARTHQUAKE, MOVE_DRAGON_CLAW, MOVE_FLAMETHROWER"),
    ("sParty_PeakLance", "MOVE_DRAGON_CLAW, MOVE_EARTHQUAKE, MOVE_ROCK_SLIDE, MOVE_AERIAL_ACE",
     "MOVE_DRAGON_CLAW, MOVE_EARTHQUAKE, MOVE_ROCK_SLIDE, MOVE_IRON_TAIL"),
    ("sParty_PeakLance", "MOVE_DRAGON_DANCE, MOVE_DRAGON_CLAW, MOVE_EARTHQUAKE, MOVE_FLAMETHROWER",
     "MOVE_DRAGON_DANCE, MOVE_DRAGON_CLAW, MOVE_EARTHQUAKE, MOVE_IRON_TAIL"),
]
p = "src/data/trainer_parties.h"
s = read(p)
for party, old, new in LANCE:
    m = re.search(r"%s\[\] = \{.*?\n\};" % party, s, re.S)
    assert m and old in m.group(0), (party, old)
    s = s[:m.start()] + m.group(0).replace(old, new, 1) + s[m.end():]
write(p, s)
print("Lance's teams given Iron Tail")
