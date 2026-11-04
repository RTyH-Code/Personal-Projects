#!/usr/bin/env python3
"""Later-generation moves for FireRed QoL+Hard (phase 3).

    python3 tools/hack/moves.py <pokemon-showdown>/data <batch>

Each batch adds a list of moves (BATCHES below). Power, accuracy, PP, type,
category, priority, target and flags come from Showdown's moves.ts; the Gen 3
battle effect, the in-game name (12 chars max), the animation and the
description are chosen here. Showdown's data files are read as text, never run.

For every move added:
  * level-up learnsets get it where the newest modern game (Gen 9 > 8 > 7)
    teaches it by level, and egg moves where Gen 4-9 have it as an egg move;
  * the modern tutor (Viridian City Pokemon Center) can teach it to every
    Pokemon that could learn it by TM or tutor in Gen 4-9. Stronger moves need
    badges: 70+ power (or a strong set-up move) needs 3, 90+ power needs 5.
  * its animation is an existing move's animation, copied and (when that
    animation leaves the background alone) tinted in the new move's type colour.

The first run also adds the tutor itself (data file, relearner hook, NPC).
"""
import re
import sys
import textwrap

SD, BATCH = sys.argv[1], sys.argv[2]

# constant, name, effect, secondary chance, animation source, description
BATCHES = {
"1": [
    ("NIGHT_SLASH", "NIGHT SLASH", "HIGH_CRITICAL", 0, "SLASH", "Slashes the foe the instant it gets a chance. High critical-hit ratio."),
    ("DARK_PULSE", "DARK PULSE", "FLINCH_HIT", 20, "PSYWAVE", "Releases an aura of evil thoughts. It may make the foe flinch."),
    ("SNARL", "SNARL", "SPECIAL_ATTACK_DOWN_HIT", 100, "ROAR", "Yells as if ranting. Lowers the foes' SP. ATK."),
    ("DRAIN_PUNCH", "DRAIN PUNCH", "ABSORB", 0, "MEGA_DRAIN", "A draining punch. The user recovers half the damage dealt."),
    ("AURA_SPHERE", "AURA SPHERE", "ALWAYS_HIT", 0, "MIST_BALL", "Looses a blast of aura power from deep within. It never misses."),
    ("FOCUS_BLAST", "FOCUS BLAST", "SPECIAL_DEFENSE_DOWN_HIT", 10, "SHADOW_BALL", "Heightens mental focus and unleashes power. May lower SP. DEF."),
    ("VACUUM_WAVE", "VACUUM WAVE", "HIT", 0, "AIR_CUTTER", "Whirls its fists to send a wave of pure vacuum. It always strikes first."),
    ("BULLET_PUNCH", "BULLET PUNCH", "HIT", 0, "MACH_PUNCH", "Punches as fast as a bullet. It always strikes first."),
    ("FORCE_PALM", "FORCE PALM", "PARALYZE_HIT", 30, "KARATE_CHOP", "A shock wave hits the foe's body. It may cause paralysis."),
    ("LOW_SWEEP", "LOW SWEEP", "SPEED_DOWN_HIT", 100, "LOW_KICK", "A swift attack on the foe's legs that lowers its SPEED."),
    ("POWER_UP_PUNCH", "POWERUPPUNCH", "ATTACK_UP_HIT", 100, "COMET_PUNCH", "Hardens the fists with each punch. Raises the user's ATTACK."),
    ("POISON_JAB", "POISON JAB", "POISON_HIT", 30, "HORN_ATTACK", "Stabs the foe with a toxic spike. It may poison the foe."),
    ("GUNK_SHOT", "GUNK SHOT", "POISON_HIT", 30, "SLUDGE_BOMB", "Shoots filthy garbage at the foe. It may poison the foe."),
    ("CROSS_POISON", "CROSS POISON", "POISON_TAIL", 10, "CROSS_CHOP", "A slashing attack that may poison. High critical-hit ratio."),
    ("EARTH_POWER", "EARTH POWER", "SPECIAL_DEFENSE_DOWN_HIT", 10, "EARTHQUAKE", "The ground under the foe erupts with power. May lower SP. DEF."),
    ("MUD_BOMB", "MUD BOMB", "ACCURACY_DOWN_HIT", 30, "MUD_SHOT", "Hurls a hard-packed mud ball. It may lower accuracy."),
    ("BULLDOZE", "BULLDOZE", "SPEED_DOWN_HIT", 100, "MAGNITUDE", "Stomps down on the ground, hitting all others and lowering SPEED."),
    ("DRILL_RUN", "DRILL RUN", "HIGH_CRITICAL", 0, "HORN_DRILL", "Crashes into the foe while spinning like a drill. High critical-hit ratio."),
    ("STONE_EDGE", "STONE EDGE", "HIGH_CRITICAL", 0, "ROCK_SLIDE", "Stabs the foe with sharpened stones. High critical-hit ratio."),
    ("POWER_GEM", "POWER GEM", "HIT", 0, "ANCIENT_POWER", "Attacks with a ray of light that sparkles like gemstones."),
    ("ROCK_POLISH", "ROCK POLISH", "SPEED_UP_2", 0, "AGILITY", "Polishes its body to reduce drag. Sharply raises SPEED."),
    ("X_SCISSOR", "X-SCISSOR", "HIT", 0, "CROSS_CHOP", "Slashes the foe by crossing its scythes or claws like scissors."),
    ("BUG_BUZZ", "BUG BUZZ", "SPECIAL_DEFENSE_DOWN_HIT", 10, "HYPER_VOICE", "Vibrates its wings to make a damaging sound wave. May lower SP. DEF."),
    ("SIGNAL_BEAM", "SIGNAL BEAM", "CONFUSE_HIT", 10, "AURORA_BEAM", "Fires a sinister beam of light. It may confuse the foe."),
    ("STRUGGLE_BUG", "STRUGGLE BUG", "SPECIAL_ATTACK_DOWN_HIT", 100, "FURY_CUTTER", "Resists to hit the foes. Lowers their SP. ATK."),
    ("LUNGE", "LUNGE", "ATTACK_DOWN_HIT", 100, "TAKE_DOWN", "Lunges at the foe with full force. Lowers the foe's ATTACK."),
    ("SHADOW_CLAW", "SHADOW CLAW", "HIGH_CRITICAL", 0, "CRUSH_CLAW", "Slashes with a sharp claw made from shadows. High critical-hit ratio."),
    ("SHADOW_SNEAK", "SHADOW SNEAK", "HIT", 0, "FAINT_ATTACK", "Extends its shadow to attack from behind. It always strikes first."),
    ("OMINOUS_WIND", "OMINOUS WIND", "ALL_STATS_UP_HIT", 10, "SILVER_WIND", "A repulsive wind. It may raise all the user's stats."),
    ("FLASH_CANNON", "FLASH CANNON", "SPECIAL_DEFENSE_DOWN_HIT", 10, "ZAP_CANNON", "Gathers light energy and fires it. It may lower SP. DEF."),
    ("IRON_HEAD", "IRON HEAD", "FLINCH_HIT", 30, "HEADBUTT", "Slams the foe with its steel-hard head. It may cause flinching."),
    ("MIRROR_SHOT", "MIRROR SHOT", "ACCURACY_DOWN_HIT", 30, "MIRROR_COAT", "A flash from its polished body. It may lower accuracy."),
    ("SMART_STRIKE", "SMART STRIKE", "ALWAYS_HIT", 0, "HORN_ATTACK", "Stabs the foe with a sharp horn. It never misses."),
    ("MAGNET_BOMB", "MAGNET BOMB", "ALWAYS_HIT", 0, "EGG_BOMB", "Launches steel bombs that stick to the foe. It never misses."),
    ("AUTOTOMIZE", "AUTOTOMIZE", "SPEED_UP_2", 0, "AGILITY", "Sheds part of its body to sharply raise its SPEED."),
    ("ZEN_HEADBUTT", "ZEN HEADBUTT", "FLINCH_HIT", 20, "HEADBUTT", "Focuses its will into its head and rams. It may cause flinching."),
    ("PSYCHO_CUT", "PSYCHO CUT", "HIGH_CRITICAL", 0, "SLASH", "Tears at the foe with blades of psychic power. High critical-hit ratio."),
    ("PSYCHIC_FANGS", "PSYCHICFANGS", "BRICK_BREAK", 0, "CRUNCH", "Bites with psychic power. It also breaks barriers such as REFLECT."),
    ("AQUA_TAIL", "AQUA TAIL", "HIT", 0, "IRON_TAIL", "Swings its tail like a vicious wave in a raging storm."),
    ("AQUA_JET", "AQUA JET", "HIT", 0, "QUICK_ATTACK", "Lunges at the foe at blinding speed. It always strikes first."),
    ("SCALD", "SCALD", "BURN_HIT", 30, "WATER_GUN", "Shoots boiling water at the foe. It may burn the foe."),
    ("LIQUIDATION", "LIQUIDATION", "DEFENSE_DOWN_HIT", 20, "CRABHAMMER", "Slams into the foe with full-force water. It may lower DEFENSE."),
    ("RAZOR_SHELL", "RAZOR SHELL", "DEFENSE_DOWN_HIT", 50, "SLASH", "Cuts the foe with sharp shells. It may lower DEFENSE."),
    ("ENERGY_BALL", "ENERGY BALL", "SPECIAL_DEFENSE_DOWN_HIT", 10, "MIST_BALL", "Draws power from nature and fires it. It may lower SP. DEF."),
    ("SEED_BOMB", "SEED BOMB", "HIT", 0, "EGG_BOMB", "Slams a barrage of hard-shelled seeds down on the foe."),
    ("WOOD_HAMMER", "WOOD HAMMER", "DOUBLE_EDGE", 0, "SLAM", "Slams its rugged body into the foe. The user is also hurt."),
    ("POWER_WHIP", "POWER WHIP", "HIT", 0, "VINE_WHIP", "Violently whirls its vines or tentacles to lash the foe."),
    ("LEAF_STORM", "LEAF STORM", "OVERHEAT", 0, "MAGICAL_LEAF", "A storm of sharp leaves. The recoil sharply lowers the user's SP. ATK."),
    ("HORN_LEECH", "HORN LEECH", "ABSORB", 0, "GIGA_DRAIN", "Drains energy with its horns. The user recovers half the damage dealt."),
    ("GRASS_KNOT", "GRASS KNOT", "LOW_KICK", 0, "GRASS_WHISTLE", "Snares the foe with grass. The heavier the foe, the stronger it is."),
    ("PETAL_BLIZZARD", "PETALBLIZZRD", "HIT", 0, "PETAL_DANCE", "Stirs up a violent petal blizzard that hits all other POKéMON."),
    ("LAVA_PLUME", "LAVA PLUME", "BURN_HIT", 30, "ERUPTION", "Scarlet flames torch everything around. It may cause a burn."),
    ("MYSTICAL_FIRE", "MYSTICALFIRE", "SPECIAL_ATTACK_DOWN_HIT", 100, "FLAMETHROWER", "Breathes a special hot fire. Lowers the foe's SP. ATK."),
    ("SCORCHING_SANDS", "SCORCH SANDS", "BURN_HIT", 30, "MUD_SHOT", "Throws scorching sand at the foe. It may cause a burn."),
    ("DISCHARGE", "DISCHARGE", "PARALYZE_HIT", 30, "THUNDERBOLT", "A loose flare of electricity hits all others. It may paralyze."),
    ("ELECTROWEB", "ELECTROWEB", "SPEED_DOWN_HIT", 100, "SPIDER_WEB", "Snares the foes in an electric net. Lowers their SPEED."),
    ("NUZZLE", "NUZZLE", "PARALYZE_HIT", 100, "SPARK", "Nuzzles the foe with electrified cheeks. It paralyzes the foe."),
    ("WILD_CHARGE", "WILD CHARGE", "RECOIL", 0, "VOLT_TACKLE", "Shrouds itself in electricity and charges. The user is also hurt."),
    ("EERIE_IMPULSE", "EERIEIMPULSE", "SPECIAL_ATTACK_DOWN_2", 0, "CHARGE", "Exposes the foe to an eerie impulse. Sharply lowers its SP. ATK."),
    ("ICE_SHARD", "ICE SHARD", "HIT", 0, "ICICLE_SPEAR", "Hurls flash-frozen chunks of ice. It always strikes first."),
    ("ICICLE_CRASH", "ICICLE CRASH", "FLINCH_HIT", 30, "ROCK_SLIDE", "Drops large icicles on the foe. It may cause flinching."),
    ("AVALANCHE", "AVALANCHE", "REVENGE", 0, "ROCK_TOMB", "Strikes last. Double power if the user was hurt by the foe this turn."),
    ("DRAGON_PULSE", "DRAGON PULSE", "HIT", 0, "DRAGON_RAGE", "Generates a shock wave from its wide-open mouth."),
    ("DRACO_METEOR", "DRACO METEOR", "OVERHEAT", 0, "ROCK_SLIDE", "Calls comets down from the sky. Sharply lowers the user's SP. ATK."),
    ("DRAGON_RUSH", "DRAGON RUSH", "FLINCH_HIT", 20, "TAKE_DOWN", "Tackles with overwhelming menace. It may cause flinching."),
    ("DUAL_CHOP", "DUAL CHOP", "DOUBLE_HIT", 0, "KARATE_CHOP", "Hits the foe with brutal strikes. It hits twice in a row."),
    ("BREAKING_SWIPE", "BREAKINGSWPE", "ATTACK_DOWN_HIT", 100, "DRAGON_CLAW", "Swings its tough tail wildly at the foes. Lowers their ATTACK."),
    ("AIR_SLASH", "AIR SLASH", "FLINCH_HIT", 30, "AIR_CUTTER", "Attacks with a blade of air that slices the sky. May cause flinching."),
    ("BRAVE_BIRD", "BRAVE BIRD", "DOUBLE_EDGE", 0, "AERIAL_ACE", "Tucks its wings and charges from a low altitude. The user is also hurt."),
    ("DUAL_WINGBEAT", "DUALWINGBEAT", "DOUBLE_HIT", 0, "WING_ATTACK", "Slams the foe with its wings. It hits twice in a row."),
    ("GIGA_IMPACT", "GIGA IMPACT", "RECHARGE", 0, "DOUBLE_EDGE", "Charges with all its might. The user must rest on the next turn."),
    ("BOOMBURST", "BOOMBURST", "HIT", 0, "HYPER_VOICE", "Attacks everything around it with a destructive sound wave."),
    ("DOUBLE_HIT", "DOUBLE HIT", "DOUBLE_HIT", 0, "POUND", "Slams the foe with its tail or similar. It hits twice in a row."),
    ("ROCK_CLIMB", "ROCK CLIMB", "CONFUSE_HIT", 20, "TAKE_DOWN", "A charging attack that may confuse the foe."),
    ("NASTY_PLOT", "NASTY PLOT", "SPECIAL_ATTACK_UP_2", 0, "TORMENT", "Thinks bad thoughts to sharply raise its SP. ATK."),
    ("BABY_DOLL_EYES", "BABYDOLLEYES", "ATTACK_DOWN", 0, "CHARM", "Stares with baby-doll eyes to lower ATTACK. Always goes first."),
],
}

TINT = {"DARK": "RGB(6, 3, 10)", "FIGHTING": "RGB(24, 8, 4)", "POISON": "RGB(20, 6, 24)", "GROUND": "RGB(22, 16, 6)",
        "ROCK": "RGB(18, 14, 8)", "BUG": "RGB(14, 22, 4)", "GHOST": "RGB(10, 6, 18)", "STEEL": "RGB(20, 20, 24)",
        "PSYCHIC": "RGB(31, 12, 22)", "WATER": "RGB(6, 14, 31)", "GRASS": "RGB(8, 24, 8)", "FIRE": "RGB(31, 12, 2)",
        "ELECTRIC": "RGB(31, 28, 4)", "ICE": "RGB(16, 28, 31)", "DRAGON": "RGB(12, 6, 28)", "FLYING": "RGB(20, 24, 31)",
        "FAIRY": "RGB(31, 19, 24)", "NORMAL": None}
TARGETS = {"normal": "MOVE_TARGET_SELECTED", "any": "MOVE_TARGET_SELECTED", "adjacentFoe": "MOVE_TARGET_SELECTED",
           "allAdjacentFoes": "MOVE_TARGET_BOTH", "allAdjacent": "MOVE_TARGET_FOES_AND_ALLY", "self": "MOVE_TARGET_USER",
           "randomNormal": "MOVE_TARGET_RANDOM", "foeSide": "MOVE_TARGET_OPPONENTS_FIELD", "allySide": "MOVE_TARGET_USER",
           "all": "MOVE_TARGET_USER", "adjacentAllyOrSelf": "MOVE_TARGET_USER", "allies": "MOVE_TARGET_USER"}
STRONG_SETUP = {"NASTY_PLOT", "SHELL_SMASH", "QUIVER_DANCE", "SHIFT_GEAR", "COIL", "COTTON_GUARD", "TAIL_GLOW"}
TUTOR_FIRST = "MOVE_FAIRY_WIND"


def read(p):
    return open(p, encoding="utf-8").read()


def write(p, s):
    open(p, "w", encoding="utf-8").write(s)


def edit(p, old, new, count=1):
    s = read(p)
    assert s.count(old) >= 1, (p, old)
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


def wrap(desc):
    lines = textwrap.wrap(desc, 19)
    assert len(lines) <= 4, desc
    return "\\n".join(lines)


# ---------------------------------------------------------------- Showdown data
SDMOVES = {}
for key, body in ts_entries(SD + "/moves.ts"):
    t = "\n".join(body)
    def f(name, t=t):
        m = re.search(r"^\t\t%s: (.*),$" % name, t, re.M)
        return m.group(1).strip('"') if m else None
    flags = re.search(r"^\t\tflags: \{(.*)\},$", t, re.M)
    SDMOVES[key] = dict(acc=f("accuracy"), power=int(f("basePower") or 0), cat=f("category"), pp=int(f("pp") or 0),
                        prio=int(f("priority") or 0), target=f("target"), type=f("type"),
                        flags=set(re.findall(r"(\w+): 1", flags.group(1))) if flags else set())

LEARN = {}
for key, body in ts_entries(SD + "/learnsets.ts"):
    moves = {}
    for line in body:
        m = re.match(r"^\t\t\t(\w+): \[(.*)\],?$", line)
        if m:
            moves[m.group(1)] = re.findall(r'"(\d)([A-Z])(\d*)"', m.group(2))
    LEARN[key] = moves

ptrs = dict(re.findall(r"\[(SPECIES_\w+)\] = (s\w+LevelUpLearnset)",
                       read("src/data/pokemon/level_up_learnset_pointers.h")))
SPECIES = [sp for sp in re.findall(r"#define (SPECIES_\w+) \d+", read("include/constants/species.h"))
           if sp not in ("SPECIES_NONE", "SPECIES_EGG") and not sp.startswith("SPECIES_OLD_UNOWN")
           and not sp.startswith("SPECIES_UNOWN_")]


def sd_species(sp):
    return LEARN.get(norm(sp[8:]), {})


def tutorable(ls, key):
    return any(kind in "MT" and g in "456789" for g, kind, _ in ls.get(key, []))


NEW = BATCHES[BATCH]
for c, name, *_ in NEW:
    assert len(name) <= 12, name
    assert norm(c) in SDMOVES, c

# drop moves that already exist or that no Gen 1-3 Pokemon can learn in any way
EXISTING = set(re.findall(r"#define MOVE_(\w+) \d+", read("include/constants/moves.h")))
keep = []
for entry in NEW:
    key = norm(entry[0])
    if entry[0] in EXISTING:
        print("already in the game, skipped:", entry[0])
    elif any(key in sd_species(sp) for sp in SPECIES):
        keep.append(entry)
    else:
        print("no learners, skipped:", entry[0])
NEW = keep

# ---------------------------------------------------------------- constants
p = "include/constants/moves.h"
s = read(p)
cnt = int(re.search(r"#define MOVES_COUNT (\d+)", s).group(1))
first = cnt
assert first + len(NEW) - 1 <= 0x1FF, "move ids must fit in 9 bits (level-up learnsets)"
defs = "".join(f"#define MOVE_{c} {first + i}\n" for i, (c, *_) in enumerate(NEW))
s = s.replace("\n#define MOVES_COUNT", f"\n// FireRed QoL+Hard: later moves, batch {BATCH} (tools/hack/moves.py)\n{defs}\n#define MOVES_COUNT", 1)
s = re.sub(r"#define MOVES_COUNT \d+", "#define MOVES_COUNT %d" % (first + len(NEW)), s)
write(p, s)

# ---------------------------------------------------------------- move data
p = "src/data/battle_moves.h"
s = read(p).rstrip()
assert s.endswith("};")
blocks = ""
for c, name, eff, chance, anim, desc in NEW:
    d = SDMOVES[norm(c)]
    status = d["cat"] == "Status"
    power = d["power"] if not status else 0
    if not status and power == 0:
        power = 1
    acc = 0 if d["acc"] == "true" else int(d["acc"])
    fl = []
    if "contact" in d["flags"]:
        fl.append("FLAG_MAKES_CONTACT")
    if "protect" in d["flags"]:
        fl.append("FLAG_PROTECT_AFFECTED")
    if "reflectable" in d["flags"]:
        fl.append("FLAG_MAGIC_COAT_AFFECTED")
    if "snatch" in d["flags"]:
        fl.append("FLAG_SNATCH_AFFECTED")
    if "mirror" in d["flags"]:
        fl.append("FLAG_MIRROR_MOVE_AFFECTED")
    if not status and chance == 0 and eff != "FLINCH_HIT":
        fl.append("FLAG_KINGS_ROCK_AFFECTED")
    split = "SPLIT_STATUS" if status else "SPLIT_" + d["cat"].upper()
    blocks += f"""
    [MOVE_{c}] =
    {{
        .effect = EFFECT_{eff},
        .power = {power},
        .type = TYPE_{d['type'].upper()},
        .accuracy = {acc},
        .pp = {d['pp']},
        .secondaryEffectChance = {chance},
        .target = {TARGETS[d['target']]},
        .priority = {d['prio']},
        .flags = {' | '.join(fl) or '0'},
        .split = {split},
    }},
"""
write(p, s[:-2].rstrip() + "\n" + blocks + "};\n")

p = "src/data/text/move_names.h"
s = read(p).rstrip()
s = s[:-2].rstrip().rstrip(",") + ",\n" + "".join(f'    [MOVE_{c}] = _("{name}"),\n' for c, name, *_ in NEW) + "};\n"
write(p, s)


def dname(c):
    return "gMoveDescription_" + c.title().replace("_", "")


p = "src/move_descriptions.c"
s = read(p)
descs = "".join(f'const u8 {dname(c)}[] = _("{wrap(d)}");\n' for c, *_, d in NEW)
s = s.replace("const u8 *const gMoveDescriptionPointers[MOVES_COUNT - 1] = {", descs + "\nconst u8 *const gMoveDescriptionPointers[MOVES_COUNT - 1] = {", 1)
s = s.rstrip()
s = s[:-2].rstrip() + "\n" + "".join(f'    [MOVE_{c} - 1] = {dname(c)},\n' for c, *_ in NEW) + "};\n"
write(p, s)

# move lists used by abilities (Iron Fist, Soundproof, Wind Rider)
for c, *_ in NEW:
    fl = SDMOVES[norm(c)]["flags"]
    if "sound" in fl:
        edit("src/battle_util.c", "static const u16 sSoundMovesTable[] =\n{\n", f"static const u16 sSoundMovesTable[] =\n{{\n    MOVE_{c},\n")
    if "punch" in fl:
        edit("src/pokemon.c", "    case MOVE_MACH_PUNCH: case MOVE_METEOR_MASH:", f"    case MOVE_{c}:\n    case MOVE_MACH_PUNCH: case MOVE_METEOR_MASH:")
    if "wind" in fl:
        edit("src/battle_util.c", "    case MOVE_GUST: case MOVE_TWISTER:", f"    case MOVE_{c}:\n    case MOVE_GUST: case MOVE_TWISTER:")

# ---------------------------------------------------------------- animations
p = "data/battle_anim_scripts.s"
s = read(p)
lines = s.split("\n")
NO_TINT = re.compile(r"F_PAL_BG|fadetobg|restorebg|Blend|Grayscale|ScreenToWhite|SetBg|InvertScreen")


def anim_block(src):
    start = lines.index(f"Move_{src}:")
    end = start + 1
    while end < len(lines) and not re.match(r"^Move_\w+:$", lines[end]):
        end += 1
    return lines[start + 1:end]


anims = ""
for c, name, eff, chance, src, desc in NEW:
    tint = TINT[SDMOVES[norm(c)]["type"].upper()]
    body = anim_block(src)
    text = "\n".join(body)
    labels = re.findall(r"^(\w+):$", text, re.M)
    gotos = re.findall(r"^\t(?:goto|jumpif\w*|choosetwoturnanim|jumpargeq|jumprettrue)\b.*?(\w+)$", text, re.M)
    external = [g for g in gotos if g not in labels and g != f"Move_{src}"]
    if not tint or NO_TINT.search(text) or "\tend" not in text or external:
        anims += f"Move_{c}:\n\tgoto Move_{src}\n\n"
        continue
    for lab in labels:
        text = re.sub(r"\b%s\b" % lab, f"HackAnim_{c}_{lab}", text)
    text = re.sub(r"\bMove_%s\b" % src, f"Move_{c}", text)
    text = text.replace("\tend\n", f"\tgoto HackAnim_{c}_End\n").rstrip()
    if text.endswith("\tend"):
        text = text[:-4] + f"\tgoto HackAnim_{c}_End"
    anims += (f"Move_{c}:\n"
              f"\tcreatesprite gSimplePaletteBlendSpriteTemplate, ANIM_ATTACKER, 2, F_PAL_BG, 1, 0, 9, {tint}\n"
              f"\twaitforvisualfinish\n{text}\n"
              f"HackAnim_{c}_End:\n"
              f"\twaitforvisualfinish\n"
              f"\tcreatesprite gSimplePaletteBlendSpriteTemplate, ANIM_ATTACKER, 2, F_PAL_BG, 1, 9, 0, {tint}\n"
              f"\twaitforvisualfinish\n\tend\n\n")
m = re.search(r"(gBattleAnims_Moves::\n(?:\t\.4byte Move_\w+\n)+)", s)
s = s[:m.end()] + "".join(f"\t.4byte Move_{c}\n" for c, *_ in NEW) + s[m.end():]
anchor = "Move_PSYCHO_BOOST:\n"
s = s.replace(anchor, anims + anchor, 1)
write(p, s)

# ---------------------------------------------------------------- level-up learnsets and egg moves
NEW_KEYS = {norm(c): "MOVE_" + c for c, *_ in NEW}
p = "src/data/pokemon/level_up_learnsets.h"
s = read(p)
added, done, full = 0, set(), []
for sp, arr in ptrs.items():
    ls = sd_species(sp)
    if not ls or arr in done:
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
    room = 32 - len(entries)
    if len(new) > room:
        full.append(arr)
        new = new[:room]
    entries = sorted(entries + new, key=lambda e: e[0])
    body = "".join(f"    LEVEL_UP_MOVE({l}, {mv}),\n" for l, mv in entries)
    s = s[:m.start(1)] + body + s[m.end(1):]
    added += len(new)
    done.add(arr)
write(p, s)

p = "src/data/pokemon/egg_moves.h"
s = read(p)
egg_added = 0
for sp, body in re.findall(r"egg_moves\((\w+),(.*?)\)", s, re.S):
    ls = LEARN.get(norm(sp))
    if not ls:
        continue
    have = re.findall(r"MOVE_\w+", body)
    extra = [mv for key, mv in NEW_KEYS.items()
             if any(kind == "E" and g in "456789" for g, kind, _ in ls.get(key, [])) and mv not in have]
    extra = extra[:max(0, 10 - len(have))]
    if extra:
        s = s.replace(f"egg_moves({sp},{body})",
                      f"egg_moves({sp},{body.rstrip()},\n              " + ",\n              ".join(extra) + ")", 1)
        egg_added += len(extra)
write(p, s)
print(f"{len(NEW)} moves; {added} level-up and {egg_added} egg entries added; learnsets full: {full}")

# ---------------------------------------------------------------- modern tutor data (regenerated every batch)
s = read("include/constants/moves.h")
ids = {m: int(n) for m, n in re.findall(r"#define (MOVE_\w+) (\d+)\n", s)}
count = int(re.search(r"#define MOVES_COUNT (\d+)", s).group(1))
base = ids[TUTOR_FIRST]
tutor_moves = sorted((n, m) for m, n in ids.items() if n >= base)
nbytes = (count - base + 7) // 8
bm = read("src/data/battle_moves.h")
tiers = []
for n, mv in tutor_moves:
    blk = re.search(r"\[%s\] =\s*\{(.*?)\}," % mv, bm, re.S).group(1)
    power = int(re.search(r"\.power = (\d+)", blk).group(1))
    tiers.append(2 if power >= 90 else 1 if power >= 70 or mv[5:] in STRONG_SETUP else 0)
rows = []
for sp in SPECIES:
    ls = sd_species(sp)
    bits = [0] * nbytes
    for n, mv in tutor_moves:
        if tutorable(ls, norm(mv[5:])):
            bits[(n - base) // 8] |= 1 << ((n - base) % 8)
    if any(bits):
        rows.append(f"    [{sp}] = {{{', '.join('0x%02X' % b for b in bits)}}},\n")
write("src/data/pokemon/hack_tutor_learnsets.h",
      "// FireRed QoL+Hard: moves the modern tutor can teach (generated by tools/hack/moves.py).\n"
      "// One bit per move from MOVE_FAIRY_WIND on: set when the Pokemon could learn that\n"
      "// move by TM or tutor in Gen 4-9.\n\n"
      f"#define HACK_TUTOR_FIRST_MOVE {TUTOR_FIRST}\n#define HACK_TUTOR_MOVE_COUNT (MOVES_COUNT - {TUTOR_FIRST})\n"
      f"#define HACK_TUTOR_BYTES {nbytes}\n\n"
      "// 0 = always, 1 = needs 3 badges, 2 = needs 5 badges\n"
      f"static const u8 sHackTutorTier[] = {{{', '.join(map(str, tiers))}}};\n\n"
      "static const u8 sHackTutorLearnsets[NUM_SPECIES][HACK_TUTOR_BYTES] =\n{\n" + "".join(rows) + "};\n")
print(f"tutor data: {len(rows)} species, {len(tutor_moves)} moves")

# ---------------------------------------------------------------- tutor infrastructure (first run only)
if "Hack_GetModernTutorMoves" not in read("src/pokemon.c"):
    edit("src/pokemon.c", "static u8 AddRelearnerMove(u16 *moves, u8 count, const u16 *known, u16 move)\n",
         """#include "data/pokemon/hack_tutor_learnsets.h"

static EWRAM_DATA u8 sHackModernTutor = 0;

void Hack_StartModernTutor(void)
{
    sHackModernTutor = TRUE;
}

void Hack_EndModernTutor(void)
{
    sHackModernTutor = FALSE;
}

static u8 AddRelearnerMove(u16 *moves, u8 count, const u16 *known, u16 move);

// Moves from later games the modern tutor teaches; stronger ones need badges.
static u8 Hack_GetModernTutorMoves(struct Pokemon *mon, u16 *moves, u8 count, const u16 *known, bool8 gated)
{
    static const u8 badgesNeeded[] = {0, 3, 5};
    u16 species = GetMonData(mon, MON_DATA_SPECIES, NULL);
    u8 badges = 0;
    u16 i;

    for (i = 0; i < 8; i++)
        if (FlagGet(FLAG_BADGE01_GET + i))
            badges++;
    for (i = 0; i < HACK_TUTOR_MOVE_COUNT; i++)
        if ((sHackTutorLearnsets[species][i / 8] & (1 << (i % 8)))
         && (!gated || badges >= badgesNeeded[sHackTutorTier[i]]))
            count = AddRelearnerMove(moves, count, known, HACK_TUTOR_FIRST_MOVE + i);
    return count;
}

static u8 Hack_ModernTutorList(struct Pokemon *mon, u16 *moves)
{
    u16 known[MAX_MON_MOVES];
    u8 i;

    for (i = 0; i < MAX_MON_MOVES; i++)
        known[i] = GetMonData(mon, MON_DATA_MOVE1 + i, NULL);
    return Hack_GetModernTutorMoves(mon, moves, 0, known, TRUE);
}

static u8 AddRelearnerMove(u16 *moves, u8 count, const u16 *known, u16 move)
""")
    edit("src/pokemon.c", """            count = AddRelearnerMove(moves, count, known, Hack_GetTutorMove(i));

    return count;""", """            count = AddRelearnerMove(moves, count, known, Hack_GetTutorMove(i));

    count = Hack_GetModernTutorMoves(mon, moves, count, known, FALSE);
    return count;""")
    edit("src/pokemon.c", """    if (FlagGet(FLAG_SYS_GAME_CLEAR))
        return GetFullRelearnerMoves(mon, moves);""", """    if (sHackModernTutor)
        return Hack_ModernTutorList(mon, moves);
    if (FlagGet(FLAG_SYS_GAME_CLEAR))
        return GetFullRelearnerMoves(mon, moves);""")
    edit("src/pokemon.c", """    if (FlagGet(FLAG_SYS_GAME_CLEAR))
    {
        u16 fullMoves[MAX_RELEARNER_MOVES];
        return GetFullRelearnerMoves(mon, fullMoves);
    }""", """    if (sHackModernTutor)
    {
        u16 tutorMoves[MAX_RELEARNER_MOVES];
        return Hack_ModernTutorList(mon, tutorMoves);
    }
    if (FlagGet(FLAG_SYS_GAME_CLEAR))
    {
        u16 fullMoves[MAX_RELEARNER_MOVES];
        return GetFullRelearnerMoves(mon, fullMoves);
    }""")
    edit("include/pokemon.h", "#define MAX_RELEARNER_MOVES 160", "#define MAX_RELEARNER_MOVES 250")
    edit("data/specials.inc", "gSpecialsEnd::",
         "\tdef_special Hack_StartModernTutor\n\tdef_special Hack_EndModernTutor\ngSpecialsEnd::")
    print("tutor infrastructure added")

# ---------------------------------------------------------------- tutor NPC (first run only)
MAPDIR = "data/maps/ViridianCity_PokemonCenter_1F/"
if "EventScript_ModernTutor" not in read(MAPDIR + "scripts.inc"):
    import json
    m = json.loads(read(MAPDIR + "map.json"))
    m["object_events"].append({
        "type": "object", "graphics_id": "OBJ_EVENT_GFX_OLD_MAN_1", "x": 5, "y": 4, "elevation": 3,
        "movement_type": "MOVEMENT_TYPE_FACE_DOWN", "movement_range_x": 1, "movement_range_y": 1,
        "trainer_type": "TRAINER_TYPE_NONE", "trainer_sight_or_berry_tree_id": "0",
        "script": "ViridianCity_PokemonCenter_1F_EventScript_ModernTutor", "flag": "0"})
    write(MAPDIR + "map.json", json.dumps(m, indent=2) + "\n")
    P = "ViridianCity_PokemonCenter_1F_EventScript_ModernTutor"
    write(MAPDIR + "scripts.inc", read(MAPDIR + "scripts.inc") + f"""
@ FireRed QoL+Hard: teaches moves from later games (tools/hack/moves.py)
{P}::
	lock
	faceplayer
	msgbox Hack_Text_ModernTutorIntro, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, {P}Done
{P}ChooseMon::
	msgbox Hack_Text_ModernTutorWhichMon
	special Hack_StartModernTutor
	special ChooseMonForMoveRelearner
	waitstate
	goto_if_ge VAR_0x8004, PARTY_SIZE, {P}Done
	special IsSelectedMonEgg
	goto_if_eq VAR_RESULT, TRUE, {P}Egg
	goto_if_eq VAR_0x8005, 0, {P}NoMoves
	msgbox Hack_Text_ModernTutorWhichMove
	special TeachMoveRelearnerMove
	waitstate
	goto_if_eq VAR_0x8004, 0, {P}ChooseMon
	msgbox Hack_Text_ModernTutorAnother, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, YES, {P}ChooseMon
	goto {P}Done

{P}Egg::
	msgbox Hack_Text_ModernTutorEgg
	goto {P}ChooseMon

{P}NoMoves::
	msgbox Hack_Text_ModernTutorNoMoves
	goto {P}ChooseMon

{P}Done::
	special Hack_EndModernTutor
	msgbox Hack_Text_ModernTutorBye
	release
	end
""")
    write(MAPDIR + "text.inc", read(MAPDIR + "text.inc") + """
Hack_Text_ModernTutorIntro::
    .string "I've traveled to faraway regions and\\n"
    .string "learned the moves POKéMON use there.\\p"
    .string "I'll teach them to your POKéMON for\\n"
    .string "free! Show me more GYM BADGES and\\l"
    .string "I'll teach stronger moves.\\p"
    .string "3 BADGES for moves with 70 power or\\n"
    .string "more, 5 BADGES for 90 or more.\\p"
    .string "Shall I teach your POKéMON?$"

Hack_Text_ModernTutorWhichMon::
    .string "Which POKéMON should learn?$"

Hack_Text_ModernTutorWhichMove::
    .string "Which move should it learn?$"

Hack_Text_ModernTutorAnother::
    .string "Shall I teach another move?$"

Hack_Text_ModernTutorEgg::
    .string "An EGG can't learn moves!$"

Hack_Text_ModernTutorNoMoves::
    .string "I don't know any moves that POKéMON\\n"
    .string "can learn yet. Come back with more\\l"
    .string "BADGES, or try another POKéMON.$"

Hack_Text_ModernTutorBye::
    .string "Come back anytime!$"
""")
    print("tutor NPC added")
