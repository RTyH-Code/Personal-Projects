#!/usr/bin/env python3
"""Balance pass after the modernization (run from the repo root, after the
other tools/hack scripts):

    python3 tools/hack/balance.py

1. Boss movesets: the gym leaders, Elite Four and Champion get modern moves
   (the player can now learn them too). Early gyms are only lightly touched;
   levels and held items don't change.
2. Peak (post-game) teams get modern sets, and the later evolutions where
   they fit a leader's theme.
3. Every move given is checked against what that species can learn in this
   hack (level-up, TM/HM, tutor, egg or the modern tutor); problems are printed.
"""
import re
import sys

# party label: {species: [moves] or [[moves], [moves]] for repeated species}
#   or for peak teams: [(species, item, [moves]), ...] replacing the whole team
STORY = {
    "sParty_LeaderLtSurge": {"PIKACHU": ["SHOCK_WAVE", "QUICK_ATTACK", "DOUBLE_TEAM", "NUZZLE"],
                             "RAICHU": ["SHOCK_WAVE", "VOLT_SWITCH", "THUNDER_WAVE", "DOUBLE_KICK"]},
    "sParty_LeaderErika": {"TANGELA": ["GIGA_DRAIN", "STUN_SPORE", "BIND", "POISON_POWDER"],
                           "VILEPLUME": ["GIGA_DRAIN", "SLUDGE_BOMB", "SLEEP_POWDER", "PETAL_DANCE"]},
    "sParty_LeaderKoga": {"MUK": ["VENOSHOCK", "MINIMIZE", "TOXIC", "ACID_ARMOR"],
                          "VENOMOTH": ["PSYBEAM", "STUN_SPORE", "BUG_BUZZ", "SUPERSONIC"],
                          "WEEZING": ["VENOSHOCK", "TOXIC", "SMOKESCREEN", "SELF_DESTRUCT"]},
    "sParty_LeaderSabrina": {"MR_MIME": ["PSYBEAM", "DAZZLING_GLEAM", "LIGHT_SCREEN", "REFLECT"],
                             "ESPEON": ["PSYCHIC", "QUICK_ATTACK", "SHADOW_BALL", "DAZZLING_GLEAM"],
                             "ALAKAZAM": ["PSYCHIC", "RECOVER", "CALM_MIND", "DAZZLING_GLEAM"]},
    "sParty_LeaderBlaine": {"NINETALES": ["FLAMETHROWER", "CONFUSE_RAY", "WILL_O_WISP", "HEX"],
                            "RAPIDASH": ["FLARE_BLITZ", "STOMP", "AGILITY", "BOUNCE"],
                            "HOUNDOOM": ["FLAMETHROWER", "DARK_PULSE", "WILL_O_WISP", "SUCKER_PUNCH"],
                            "ARCANINE": ["FLAMETHROWER", "EXTREME_SPEED", "CRUNCH", "WILD_CHARGE"]},
    "sParty_LeaderGiovanni": {"SANDSLASH": ["EARTHQUAKE", "SLASH", "SAND_TOMB", "X_SCISSOR"],
                              "DUGTRIO": ["EARTHQUAKE", "SUCKER_PUNCH", "SAND_ATTACK", "STONE_EDGE"],
                              "RHYDON": ["EARTHQUAKE", "STONE_EDGE", "MEGAHORN", "SCARY_FACE"]},
    "sParty_EliteFourLorelei": {"DEWGONG": ["ICE_BEAM", "SURF", "AQUA_JET", "SAFEGUARD"],
                                "CLOYSTER": ["SHELL_SMASH", "ICICLE_SPEAR", "LIQUIDATION", "ICE_SHARD"],
                                "SLOWBRO": ["SCALD", "PSYCHIC", "AMNESIA", "YAWN"],
                                "JYNX": ["ICE_BEAM", "PSYSHOCK", "LOVELY_KISS", "NASTY_PLOT"],
                                "LAPRAS": ["ICE_BEAM", "SURF", "THUNDERBOLT", "CONFUSE_RAY"]},
    "sParty_EliteFourBruno": {"ONIX": [["EARTHQUAKE", "STONE_EDGE", "IRON_TAIL", "STEALTH_ROCK"],
                                       ["ROCK_POLISH", "EARTHQUAKE", "STONE_EDGE", "IRON_TAIL"]],
                              "HITMONCHAN": ["DRAIN_PUNCH", "MACH_PUNCH", "ICE_PUNCH", "BULLET_PUNCH"],
                              "HITMONLEE": ["HI_JUMP_KICK", "ROCK_SLIDE", "BLAZE_KICK", "FAKE_OUT"],
                              "MACHAMP": ["CLOSE_COMBAT", "BULK_UP", "KNOCK_OFF", "STONE_EDGE"]},
    "sParty_EliteFourAgatha": {"GENGAR": [["HEX", "WILL_O_WISP", "CONFUSE_RAY", "SLUDGE_BOMB"],
                                          ["SHADOW_BALL", "SLUDGE_BOMB", "HYPNOSIS", "NASTY_PLOT"]],
                               "GOLBAT": ["POISON_FANG", "AIR_SLASH", "CONFUSE_RAY", "BITE"],
                               "HAUNTER": ["HYPNOSIS", "DREAM_EATER", "HEX", "MEAN_LOOK"],
                               "ARBOK": ["GUNK_SHOT", "GLARE", "SUCKER_PUNCH", "IRON_TAIL"]},
    "sParty_EliteFourLance": {"GYARADOS": ["WATERFALL", "CRUNCH", "DRAGON_DANCE", "IRON_TAIL"],
                              "DRAGONAIR": [["DRAGON_PULSE", "IRON_TAIL", "THUNDER_WAVE", "OUTRAGE"],
                                            ["AQUA_TAIL", "SAFEGUARD", "THUNDER_WAVE", "OUTRAGE"]],
                              "AERODACTYL": ["STONE_EDGE", "AERIAL_ACE", "ICE_FANG", "CRUNCH"],
                              "DRAGONITE": ["DRAGON_DANCE", "OUTRAGE", "EXTREME_SPEED", "IRON_TAIL"]},
}
CHAMPION = {"PIDGEOT": ["HURRICANE", "STEEL_WING", "ROOST", "QUICK_ATTACK"],
            "ALAKAZAM": ["PSYCHIC", "DAZZLING_GLEAM", "CALM_MIND", "RECOVER"],
            "RHYDON": ["EARTHQUAKE", "STONE_EDGE", "MEGAHORN", "STEALTH_ROCK"],
            "ARCANINE": ["FLARE_BLITZ", "EXTREME_SPEED", "CRUNCH", "WILD_CHARGE"],
            "EXEGGUTOR": ["ENERGY_BALL", "PSYCHIC", "SLEEP_POWDER", "LEECH_SEED"],
            "GYARADOS": ["WATERFALL", "CRUNCH", "DRAGON_DANCE", "EARTHQUAKE"],
            "BLASTOISE": ["HYDRO_PUMP", "ICE_BEAM", "FLASH_CANNON", "RAPID_SPIN"],
            "CHARIZARD": ["FLAMETHROWER", "AIR_SLASH", "DRAGON_PULSE", "FOCUS_BLAST"],
            "VENUSAUR": ["GIGA_DRAIN", "SLUDGE_BOMB", "SLEEP_POWDER", "EARTH_POWER"]}
for starter in ("Squirtle", "Bulbasaur", "Charmander"):
    STORY["sParty_ChampionFirst" + starter] = CHAMPION

RIVAL_CORE = [("PIDGEOT", "SHARP_BEAK", ["BRAVE_BIRD", "U_TURN", "ROOST", "QUICK_ATTACK"]),
              ("ALAKAZAM", "TWISTED_SPOON", ["PSYCHIC", "SHADOW_BALL", "FOCUS_BLAST", "CALM_MIND"]),
              ("TYRANITAR", "LEFTOVERS", ["DRAGON_DANCE", "STONE_EDGE", "EARTHQUAKE", "CRUNCH"])]
EXEGGUTOR = ("EXEGGUTOR", "LEFTOVERS", ["ENERGY_BALL", "PSYCHIC", "SLEEP_POWDER", "EXPLOSION"])
ARCANINE = ("ARCANINE", "CHARCOAL", ["FLARE_BLITZ", "EXTREME_SPEED", "CRUNCH", "WILD_CHARGE"])
GYARADOS = ("GYARADOS", "LEFTOVERS", ["DRAGON_DANCE", "WATERFALL", "EARTHQUAKE", "CRUNCH"])
PEAK = {
    "sParty_PeakBrock": [
        ("GOLEM", "CHOICE_BAND", ["EARTHQUAKE", "STONE_EDGE", "EXPLOSION", "DOUBLE_EDGE"]),
        ("OMASTAR", "MYSTIC_WATER", ["SHELL_SMASH", "HYDRO_PUMP", "ICE_BEAM", "EARTH_POWER"]),
        ("KABUTOPS", "SCOPE_LENS", ["STONE_EDGE", "WATERFALL", "X_SCISSOR", "SWORDS_DANCE"]),
        ("PROBOPASS", "LEFTOVERS", ["POWER_GEM", "EARTH_POWER", "FLASH_CANNON", "STEALTH_ROCK"]),
        ("RHYPERIOR", "QUICK_CLAW", ["EARTHQUAKE", "STONE_EDGE", "MEGAHORN", "ROCK_POLISH"]),
        ("TYRANITAR", "LEFTOVERS", ["DRAGON_DANCE", "STONE_EDGE", "EARTHQUAKE", "CRUNCH"])],
    "sParty_PeakMisty": [
        ("GOLDUCK", "MYSTIC_WATER", ["HYDRO_PUMP", "ICE_BEAM", "PSYSHOCK", "CALM_MIND"]),
        ("LAPRAS", "LEFTOVERS", ["ICE_BEAM", "SURF", "THUNDERBOLT", "CONFUSE_RAY"]),
        ("VAPOREON", "LEFTOVERS", ["SCALD", "ICE_BEAM", "WISH", "PROTECT"]),
        ("MILOTIC", "LEFTOVERS", ["SCALD", "ICE_BEAM", "RECOVER", "TOXIC"]),
        ("GYARADOS", "LUM_BERRY", ["DRAGON_DANCE", "WATERFALL", "EARTHQUAKE", "CRUNCH"]),
        ("STARMIE", "LEFTOVERS", ["SCALD", "PSYSHOCK", "THUNDERBOLT", "RECOVER"])],
    "sParty_PeakLtSurge": [
        ("ELECTRODE", "MAGNET", ["THUNDERBOLT", "VOLT_SWITCH", "EXPLOSION", "TAUNT"]),
        ("MAGNEZONE", "LEFTOVERS", ["THUNDERBOLT", "FLASH_CANNON", "VOLT_SWITCH", "THUNDER_WAVE"]),
        ("AMPHAROS", "LEFTOVERS", ["THUNDERBOLT", "DRAGON_PULSE", "FOCUS_BLAST", "THUNDER_WAVE"]),
        ("ELECTIVIRE", "MAGNET", ["WILD_CHARGE", "ICE_PUNCH", "CROSS_CHOP", "EARTHQUAKE"]),
        ("JOLTEON", "MAGNET", ["THUNDERBOLT", "SHADOW_BALL", "VOLT_SWITCH", "AGILITY"]),
        ("RAICHU", "LEFTOVERS", ["THUNDERBOLT", "SURF", "FOCUS_BLAST", "NASTY_PLOT"])],
    "sParty_PeakErika": [
        ("BRELOOM", "QUICK_CLAW", ["SPORE", "SEED_BOMB", "MACH_PUNCH", "DRAIN_PUNCH"]),
        ("VICTREEBEL", "MIRACLE_SEED", ["POWER_WHIP", "SLUDGE_BOMB", "SLEEP_POWDER", "SWORDS_DANCE"]),
        ("EXEGGUTOR", "LEFTOVERS", ["GIGA_DRAIN", "PSYCHIC", "SLEEP_POWDER", "EXPLOSION"]),
        ("TANGROWTH", "LEFTOVERS", ["POWER_WHIP", "EARTHQUAKE", "SLEEP_POWDER", "KNOCK_OFF"]),
        ("SCEPTILE", "MIRACLE_SEED", ["LEAF_BLADE", "EARTHQUAKE", "DRAGON_CLAW", "SWORDS_DANCE"]),
        ("ROSERADE", "LEFTOVERS", ["LEAF_STORM", "SLUDGE_BOMB", "SPIKES", "SHADOW_BALL"])],
    "sParty_PeakKoga": [
        ("TENTACRUEL", "LEFTOVERS", ["SCALD", "SLUDGE_BOMB", "TOXIC_SPIKES", "RAPID_SPIN"]),
        ("VENOMOTH", "SILVER_POWDER", ["QUIVER_DANCE", "BUG_BUZZ", "SLUDGE_BOMB", "SLEEP_POWDER"]),
        ("MUK", "LEFTOVERS", ["GUNK_SHOT", "SHADOW_SNEAK", "DRAIN_PUNCH", "CURSE"]),
        ("NIDOKING", "LEFTOVERS", ["EARTH_POWER", "SLUDGE_WAVE", "ICE_BEAM", "THUNDERBOLT"]),
        ("GENGAR", "LEFTOVERS", ["SHADOW_BALL", "SLUDGE_BOMB", "FOCUS_BLAST", "DESTINY_BOND"]),
        ("WEEZING", "LEFTOVERS", ["SLUDGE_BOMB", "FIRE_BLAST", "WILL_O_WISP", "TOXIC_SPIKES"])],
    "sParty_PeakSabrina": [
        ("MR_MIME", "LEFTOVERS", ["PSYCHIC", "DAZZLING_GLEAM", "CALM_MIND", "SUBSTITUTE"]),
        ("GALLADE", "SCOPE_LENS", ["CLOSE_COMBAT", "PSYCHO_CUT", "NIGHT_SLASH", "SWORDS_DANCE"]),
        ("GARDEVOIR", "LEFTOVERS", ["MOONBLAST", "PSYCHIC", "CALM_MIND", "HYPNOSIS"]),
        ("METAGROSS", "CHOICE_BAND", ["METEOR_MASH", "EARTHQUAKE", "ZEN_HEADBUTT", "BULLET_PUNCH"]),
        ("ESPEON", "LEFTOVERS", ["PSYCHIC", "DAZZLING_GLEAM", "CALM_MIND", "MORNING_SUN"]),
        ("ALAKAZAM", "TWISTED_SPOON", ["PSYCHIC", "SHADOW_BALL", "FOCUS_BLAST", "CALM_MIND"])],
    "sParty_PeakBlaine": [
        ("RAPIDASH", "LEFTOVERS", ["FLARE_BLITZ", "WILD_CHARGE", "DRILL_RUN", "AGILITY"]),
        ("NINETALES", "LEFTOVERS", ["FLAMETHROWER", "EXTRASENSORY", "NASTY_PLOT", "WILL_O_WISP"]),
        ("MAGMORTAR", "CHARCOAL", ["FLAMETHROWER", "THUNDERBOLT", "FOCUS_BLAST", "PSYCHIC"]),
        ("HOUNDOOM", "BLACK_GLASSES", ["FLAMETHROWER", "DARK_PULSE", "NASTY_PLOT", "SLUDGE_BOMB"]),
        ("BLAZIKEN", "CHARCOAL", ["CLOSE_COMBAT", "FLARE_BLITZ", "STONE_EDGE", "SWORDS_DANCE"]),
        ("ARCANINE", "LEFTOVERS", ["FLARE_BLITZ", "EXTREME_SPEED", "CRUNCH", "WILD_CHARGE"])],
    "sParty_PeakGiovanni": [
        ("DUGTRIO", "CHOICE_BAND", ["EARTHQUAKE", "STONE_EDGE", "SUCKER_PUNCH", "AERIAL_ACE"]),
        ("SANDSLASH", "QUICK_CLAW", ["EARTHQUAKE", "STONE_EDGE", "SWORDS_DANCE", "X_SCISSOR"]),
        ("MAROWAK", "THICK_CLUB", ["EARTHQUAKE", "STONE_EDGE", "DOUBLE_EDGE", "SWORDS_DANCE"]),
        ("NIDOQUEEN", "LEFTOVERS", ["EARTH_POWER", "ICE_BEAM", "SLUDGE_WAVE", "STEALTH_ROCK"]),
        ("NIDOKING", "LEFTOVERS", ["EARTH_POWER", "SLUDGE_WAVE", "ICE_BEAM", "THUNDERBOLT"]),
        ("RHYPERIOR", "QUICK_CLAW", ["EARTHQUAKE", "STONE_EDGE", "MEGAHORN", "SWORDS_DANCE"])],
    "sParty_PeakLorelei": [
        ("MAMOSWINE", "NEVER_MELT_ICE", ["EARTHQUAKE", "ICICLE_CRASH", "ICE_SHARD", "STONE_EDGE"]),
        ("CLOYSTER", "NEVER_MELT_ICE", ["SHELL_SMASH", "ICICLE_SPEAR", "LIQUIDATION", "ICE_SHARD"]),
        ("JYNX", "NEVER_MELT_ICE", ["ICE_BEAM", "PSYCHIC", "LOVELY_KISS", "NASTY_PLOT"]),
        ("WALREIN", "LEFTOVERS", ["ICE_BEAM", "SURF", "BODY_SLAM", "REST"]),
        ("FROSLASS", "QUICK_CLAW", ["ICE_BEAM", "SHADOW_BALL", "WILL_O_WISP", "SPIKES"]),
        ("LAPRAS", "LEFTOVERS", ["ICE_BEAM", "SURF", "THUNDERBOLT", "CONFUSE_RAY"])],
    "sParty_PeakBruno": [
        ("HITMONTOP", "LEFTOVERS", ["CLOSE_COMBAT", "RAPID_SPIN", "SUCKER_PUNCH", "STONE_EDGE"]),
        ("HITMONCHAN", "BLACK_BELT", ["DRAIN_PUNCH", "ICE_PUNCH", "THUNDER_PUNCH", "BULLET_PUNCH"]),
        ("HITMONLEE", "SCOPE_LENS", ["HI_JUMP_KICK", "BLAZE_KICK", "STONE_EDGE", "BULK_UP"]),
        ("ANNIHILAPE", "LEFTOVERS", ["CLOSE_COMBAT", "SHADOW_CLAW", "BULK_UP", "U_TURN"]),
        ("HERACROSS", "CHOICE_BAND", ["MEGAHORN", "CLOSE_COMBAT", "STONE_EDGE", "EARTHQUAKE"]),
        ("MACHAMP", "LEFTOVERS", ["CLOSE_COMBAT", "KNOCK_OFF", "STONE_EDGE", "BULLET_PUNCH"])],
    "sParty_PeakAgatha": [
        ("SABLEYE", "LEFTOVERS", ["KNOCK_OFF", "SHADOW_CLAW", "FOUL_PLAY", "RECOVER"]),
        ("MISMAGIUS", "LEFTOVERS", ["SHADOW_BALL", "DAZZLING_GLEAM", "NASTY_PLOT", "THUNDERBOLT"]),
        ("DUSKNOIR", "LEFTOVERS", ["SHADOW_SNEAK", "ICE_PUNCH", "EARTHQUAKE", "WILL_O_WISP"]),
        ("BANETTE", "SPELL_TAG", ["KNOCK_OFF", "SHADOW_CLAW", "WILL_O_WISP", "SHADOW_SNEAK"]),
        ("CROBAT", "SHARP_BEAK", ["BRAVE_BIRD", "CROSS_POISON", "U_TURN", "ROOST"]),
        ("GENGAR", "LEFTOVERS", ["SHADOW_BALL", "SLUDGE_BOMB", "FOCUS_BLAST", "NASTY_PLOT"])],
    "sParty_PeakLance": [
        ("KINGDRA", "MYSTIC_WATER", ["HYDRO_PUMP", "DRACO_METEOR", "ICE_BEAM", "RAIN_DANCE"]),
        ("AERODACTYL", "SCOPE_LENS", ["STONE_EDGE", "EARTHQUAKE", "ICE_FANG", "DOUBLE_EDGE"]),
        ("ALTARIA", "LEFTOVERS", ["DRAGON_DANCE", "DRAGON_CLAW", "EARTHQUAKE", "ROOST"]),
        ("FLYGON", "SOFT_SAND", ["EARTHQUAKE", "DRAGON_CLAW", "U_TURN", "FIRE_BLAST"]),
        ("SALAMENCE", "CHOICE_BAND", ["OUTRAGE", "EARTHQUAKE", "FIRE_FANG", "AERIAL_ACE"]),
        ("DRAGONITE", "LEFTOVERS", ["DRAGON_DANCE", "OUTRAGE", "EXTREME_SPEED", "EARTHQUAKE"])],
    "sParty_PeakChampionSquirtle": RIVAL_CORE + [EXEGGUTOR, ARCANINE,
        ("BLASTOISE", "LEFTOVERS", ["SHELL_SMASH", "HYDRO_PUMP", "ICE_BEAM", "DARK_PULSE"])],
    "sParty_PeakChampionBulbasaur": RIVAL_CORE + [GYARADOS, ARCANINE,
        ("VENUSAUR", "LEFTOVERS", ["GIGA_DRAIN", "SLUDGE_BOMB", "SLEEP_POWDER", "EARTH_POWER"])],
    "sParty_PeakChampionCharmander": RIVAL_CORE + [EXEGGUTOR, GYARADOS,
        ("CHARIZARD", "CHARCOAL", ["FLAMETHROWER", "AIR_SLASH", "DRAGON_PULSE", "FOCUS_BLAST"])],
}


def read(p):
    return open(p, encoding="utf-8").read()


# ---------------------------------------------------------------- what each species can learn in this hack
lu_ptr = dict(re.findall(r"\[(SPECIES_\w+)\] = (s\w+LevelUpLearnset)", read("src/data/pokemon/level_up_learnset_pointers.h")))
lu = {n: set(re.findall(r"MOVE_\w+", b)) for n, b in re.findall(r"static const u16 (s\w+LevelUpLearnset)\[\] = \{(.*?)\};", read("src/data/pokemon/level_up_learnsets.h"), re.S)}
tm_moves = {}
for name in re.findall(r"#define ITEM_((?:TM|HM)\d\d_\w+)", read("include/constants/items.h")):
    tm_moves[name] = "MOVE_" + name.split("_", 1)[1]
tmhm = {sp: {tm_moves.get(t, "MOVE_" + t.split("_", 1)[1]) for t in re.findall(r"TMHM\(((?:TM|HM)\d\d_\w+)\)", b)}
        for sp, b in re.findall(r"\[(SPECIES_\w+)\]\s*= TMHM_LEARNSET\((.*?)\),\n", read("src/data/pokemon/tmhm_learnsets.h"), re.S)}
tutor = {sp: set(re.findall(r"TUTOR\((MOVE_\w+)\)", b)) for sp, b in re.findall(r"\[(SPECIES_\w+)\] = (TUTOR.*?),\n\n", read("src/data/pokemon/tutor_learnsets.h"), re.S)}
egg = {"SPECIES_" + sp: set(re.findall(r"MOVE_\w+", b)) for sp, b in re.findall(r"egg_moves\((\w+),(.*?)\)", read("src/data/pokemon/egg_moves.h"), re.S)}
move_ids = {m: int(n) for m, n in re.findall(r"#define (MOVE_\w+) (\d+)\n", read("include/constants/moves.h"))}
by_id = {v: k for k, v in move_ids.items()}
ht = read("src/data/pokemon/hack_tutor_learnsets.h")
first = move_ids[re.search(r"#define HACK_TUTOR_FIRST_MOVE (MOVE_\w+)", ht).group(1)]
modern = {}
for sp, body in re.findall(r"\[(SPECIES_\w+)\] = \{(.*?)\}", ht):
    bits = [int(b, 16) for b in body.split(",")]
    modern[sp] = {by_id[first + i] for i in range(len(bits) * 8) if bits[i // 8] & (1 << (i % 8)) and first + i in by_id}
evo = read("src/data/pokemon/evolution.h")
prevo = {}
for a, body in re.findall(r"\[(SPECIES_\w+)\]\s*=\s*\{(.*?)\}\},", evo, re.S):
    for t in re.findall(r"(SPECIES_\w+)\}", body + "}"):
        prevo[t] = a


def learnable(sp):
    out, s = set(), sp
    while s:
        out |= lu.get(lu_ptr.get(s), set()) | tmhm.get(s, set()) | tutor.get(s, set()) | egg.get(s, set()) | modern.get(s, set())
        s = prevo.get(s)
    return out


warnings = []


def check(party, sp, moves):
    can = learnable("SPECIES_" + sp)
    for m in moves:
        if "MOVE_" + m not in move_ids:
            sys.exit(f"{party} {sp}: unknown move {m}")
        if "MOVE_" + m not in can:
            warnings.append(f"{party} {sp}: can't normally learn {m}")


# ---------------------------------------------------------------- apply
p = "src/data/trainer_parties.h"
s = read(p)
for party, sets in STORY.items():
    m = re.search(r"(%s\[\] = \{)(.*?)(\n\};)" % party, s, re.S)
    assert m, party
    seen = {}
    def mon(mm):
        sp = re.search(r"\.species = SPECIES_(\w+)", mm.group(0)).group(1)
        if sp not in sets:
            return mm.group(0)
        mv = sets[sp]
        if isinstance(mv[0], list):
            mv = mv[min(seen.get(sp, 0), len(mv) - 1)]
        seen[sp] = seen.get(sp, 0) + 1
        check(party, sp, mv)
        return re.sub(r"\.moves = \{[^}]*\}", ".moves = {%s}" % ", ".join("MOVE_" + x for x in mv), mm.group(0))
    body = re.sub(r"    \{\n.*?\n    \}", mon, m.group(2), flags=re.S)
    s = s[:m.start(2)] + body + s[m.end(2):]
for party, team in PEAK.items():
    m = re.search(r"(%s\[\] = \{)(.*?)(\n\};)" % party, s, re.S)
    assert m, party
    mons = re.findall(r"    \{\n.*?\n    \}", m.group(2), re.S)
    assert len(mons) == len(team), party
    new = []
    for old, (sp, item, mv) in zip(mons, team):
        check(party, sp, mv)
        o = re.sub(r"\.species = SPECIES_\w+", f".species = SPECIES_{sp}", old)
        o = re.sub(r"\.heldItem = ITEM_\w+", f".heldItem = ITEM_{item}", o)
        o = re.sub(r"\.moves = \{[^}]*\}", ".moves = {%s}" % ", ".join("MOVE_" + x for x in mv), o)
        new.append(o)
    s = s[:m.start(2)] + "\n" + ",\n".join(new) + "," + s[m.end(2):]
# Leech Life went from 20 to 80 power: a Rocket Grunt's Lv. 20 Zubat get Absorb (as a modern
# Zubat would know at that level) instead of the custom Leech Life they had in FireRed.
m = re.search(r"(sParty_TeamRocketGrunt13\[\] = \{)(.*?)(\n\};)", s, re.S)
s = s[:m.start(2)] + m.group(2).replace("MOVE_LEECH_LIFE", "MOVE_ABSORB") + s[m.end(2):]
open(p, "w", encoding="utf-8").write(s)

# ...and, as in Gen 9, it is no longer an egg move (Bellsprout and Yanma would hatch with it at Lv. 5)
e = read("src/data/pokemon/egg_moves.h")
for sp in ("BELLSPROUT", "YANMA"):
    m = re.search(r"egg_moves\(%s,(.*?)\)" % sp, e, re.S)
    body = re.sub(r"\s*MOVE_LEECH_LIFE,?", "", m.group(1)).rstrip().rstrip(",")
    e = e[:m.start(1)] + body + e[m.end(1):]
open("src/data/pokemon/egg_moves.h", "w", encoding="utf-8").write(e)
for w in warnings:
    print("warning:", w)
print(f"{len(STORY)} story parties and {len(PEAK)} peak teams updated, {len(warnings)} warnings")
