#!/usr/bin/env python3
"""Difficulty pass for the FireRed QoL+Hard hack.

1. Replaces the 8 Gym Leader parties with bigger, held-item teams.
2. Scales every other real (FRLG) trainer's levels by LEVEL_SCALE and
   raises IVs: regular trainers get at least MIN_IV, bosses get max IVs.
3. Gives every trainer the "smart" AI flags.
Run once from the repo root: python3 tools/hack/difficulty.py
"""
import re

LEVEL_SCALE = 1.15
MIN_IV = 150          # 0-255 scale -> ~18 IVs per stat
BOSS_IV = 255         # 31 IVs
SMART_AI = "AI_SCRIPT_CHECK_BAD_MOVE | AI_SCRIPT_TRY_TO_FAINT | AI_SCRIPT_CHECK_VIABILITY"

# name: [(lvl, species, item, [moves])]
GYMS = {
 "LeaderBrock": [
  (13, "GEODUDE", "NONE", ["ROCK_THROW", "DEFENSE_CURL", "TACKLE", "MUD_SPORT"]),
  (13, "RHYHORN", "NONE", ["HORN_ATTACK", "TAIL_WHIP", "ROCK_TOMB", "STOMP"]),
  (16, "ONIX", "ORAN_BERRY", ["ROCK_TOMB", "BIND", "SCREECH", "TACKLE"]),
 ],
 "LeaderMisty": [
  (19, "PSYDUCK", "NONE", ["CONFUSION", "WATER_GUN", "DISABLE", "SCRATCH"]),
  (19, "GOLDEEN", "NONE", ["HORN_ATTACK", "WATER_PULSE", "SUPERSONIC", "PECK"]),
  (20, "STARYU", "NONE", ["WATER_PULSE", "SWIFT", "RECOVER", "HARDEN"]),
  (23, "STARMIE", "SITRUS_BERRY", ["WATER_PULSE", "RECOVER", "RAPID_SPIN", "SWIFT"]),
 ],
 "LeaderLtSurge": [
  (24, "VOLTORB", "NONE", ["SONIC_BOOM", "SPARK", "SCREECH", "SELF_DESTRUCT"]),
  (24, "MAGNEMITE", "NONE", ["SHOCK_WAVE", "SONIC_BOOM", "THUNDER_WAVE", "SUPERSONIC"]),
  (25, "PIKACHU", "NONE", ["SHOCK_WAVE", "QUICK_ATTACK", "DOUBLE_TEAM", "THUNDER_WAVE"]),
  (28, "RAICHU", "MAGNET", ["SHOCK_WAVE", "QUICK_ATTACK", "THUNDER_WAVE", "DOUBLE_KICK"]),
 ],
 "LeaderErika": [
  (31, "TANGELA", "NONE", ["MEGA_DRAIN", "STUN_SPORE", "BIND", "POISON_POWDER"]),
  (31, "WEEPINBELL", "NONE", ["RAZOR_LEAF", "ACID", "SLEEP_POWDER", "WRAP"]),
  (32, "EXEGGCUTE", "NONE", ["HYPNOSIS", "STUN_SPORE", "CONFUSION", "LEECH_SEED"]),
  (33, "VICTREEBEL", "NONE", ["RAZOR_LEAF", "ACID", "SLEEP_POWDER", "WRAP"]),
  (35, "VILEPLUME", "MIRACLE_SEED", ["GIGA_DRAIN", "ACID", "SLEEP_POWDER", "PETAL_DANCE"]),
 ],
 "LeaderKoga": [
  (40, "KOFFING", "NONE", ["SLUDGE", "SMOKESCREEN", "SELF_DESTRUCT", "TOXIC"]),
  (40, "MUK", "NONE", ["SLUDGE", "MINIMIZE", "TOXIC", "ACID_ARMOR"]),
  (41, "VENOMOTH", "NONE", ["PSYBEAM", "STUN_SPORE", "LEECH_LIFE", "SUPERSONIC"]),
  (41, "GOLBAT", "NONE", ["WING_ATTACK", "CONFUSE_RAY", "BITE", "LEECH_LIFE"]),
  (45, "WEEZING", "POISON_BARB", ["SLUDGE", "TOXIC", "SMOKESCREEN", "SELF_DESTRUCT"]),
 ],
 "LeaderSabrina": [
  (42, "KADABRA", "NONE", ["PSYBEAM", "RECOVER", "REFLECT", "FUTURE_SIGHT"]),
  (42, "MR_MIME", "NONE", ["PSYBEAM", "BARRIER", "LIGHT_SCREEN", "REFLECT"]),
  (43, "HYPNO", "NONE", ["PSYCHIC", "HYPNOSIS", "HEADBUTT", "POISON_GAS"]),
  (43, "ESPEON", "NONE", ["PSYCHIC", "QUICK_ATTACK", "BITE", "SWIFT"]),
  (47, "ALAKAZAM", "TWISTED_SPOON", ["PSYCHIC", "RECOVER", "CALM_MIND", "FUTURE_SIGHT"]),
 ],
 "LeaderBlaine": [
  (46, "NINETALES", "NONE", ["FLAMETHROWER", "CONFUSE_RAY", "WILL_O_WISP", "QUICK_ATTACK"]),
  (46, "RAPIDASH", "NONE", ["FIRE_BLAST", "STOMP", "AGILITY", "BOUNCE"]),
  (47, "MAGMAR", "NONE", ["FIRE_PUNCH", "THUNDER_PUNCH", "CONFUSE_RAY", "SMOKESCREEN"]),
  (47, "HOUNDOOM", "NONE", ["FLAMETHROWER", "CRUNCH", "ROAR", "SMOG"]),
  (51, "ARCANINE", "CHARCOAL", ["FLAMETHROWER", "EXTREME_SPEED", "BITE", "ROAR"]),
 ],
 "LeaderGiovanni": [
  (49, "SANDSLASH", "NONE", ["EARTHQUAKE", "SLASH", "SAND_TOMB", "SWIFT"]),
  (49, "DUGTRIO", "NONE", ["EARTHQUAKE", "SLASH", "SAND_ATTACK", "FURY_SWIPES"]),
  (50, "NIDOQUEEN", "NONE", ["EARTHQUAKE", "BODY_SLAM", "SUPERPOWER", "CRUNCH"]),
  (50, "NIDOKING", "NONE", ["EARTHQUAKE", "MEGAHORN", "ICE_BEAM", "THUNDERBOLT"]),
  (51, "MAROWAK", "THICK_CLUB", ["BONEMERANG", "ROCK_SLIDE", "FOCUS_ENERGY", "HEADBUTT"]),
  (54, "RHYDON", "SOFT_SAND", ["EARTHQUAKE", "ROCK_SLIDE", "MEGAHORN", "SCARY_FACE"]),
 ],
}
BOSS_RE = re.compile(r"sParty_(Leader|EliteFour|Champion|Rival|Boss)")

def gym_block(name, mons):
    out = [f"static const struct TrainerMonItemCustomMoves sParty_{name}[] = {{"]
    for lvl, sp, item, moves in mons:
        mv = ", ".join("MOVE_" + m for m in moves)
        out += ["    {", f"        .iv = {BOSS_IV},", f"        .lvl = {lvl},",
                f"        .species = SPECIES_{sp},", f"        .heldItem = ITEM_{item},",
                f"        .moves = {{{mv}}},", "    },"]
    return "\n".join(out + ["};"])

parties = open("src/data/trainer_parties.h").read()
for name, mons in GYMS.items():
    parties, n = re.subn(r"static const struct \w+ sParty_%s\[\] = \{.*?\n\};" % name,
                         lambda m: gym_block(name, mons), parties, count=1, flags=re.S)
    assert n == 1, name

def scale_party(m):
    name, body = m.group(1), m.group(2)
    if name in GYMS or "DUMMY_TRAINER" in body:
        return m.group(0)
    boss = BOSS_RE.match("sParty_" + name)
    body = re.sub(r"\.lvl = (\d+)", lambda l: ".lvl = %d" % min(100, round(int(l.group(1)) * LEVEL_SCALE)), body)
    body = re.sub(r"\.iv = (\d+)", lambda i: ".iv = %d" % (BOSS_IV if boss else max(MIN_IV, int(i.group(1)))), body)
    return m.group(0)[:m.start(2) - m.start(0)] + body + m.group(0)[m.end(2) - m.start(0):]

parties = re.sub(r"static const struct \w+ sParty_(\w+)\[\] = \{(.*?)\n\};", scale_party, parties, flags=re.S)
open("src/data/trainer_parties.h", "w").write(parties)

trainers = open("src/data/trainers.h").read()
for name in GYMS:
    trainers, n = re.subn(r"\w+\(sParty_%s\)" % name, "ITEM_CUSTOM_MOVES(sParty_%s)" % name, trainers)
    assert n == 1, name
trainers = re.sub(r"\.aiFlags = [^,]+,", ".aiFlags = %s," % SMART_AI, trainers)
open("src/data/trainers.h", "w").write(trainers)
print("difficulty pass applied")
