#!/usr/bin/env python3
"""Peak trainers: post-game Lv. 100 rematches.

* After becoming Champion, each Gym Leader offers unlimited rematches with a
  themed team of six Lv. 100 Gen 1-3 Pokemon.
* A League official in the Indigo Plateau Pokemon Center toggles a "peak"
  Elite Four + Champion challenge (round 3).
Peak Pokemon get max IVs; the battle code (F_TRAINER_PARTY_PEAK in
battle_main.c) gives them a matching nature and 252/252 EVs.

The peak trainers reuse the unused Ruby/Sapphire placeholder trainer slots.

Run once from the repo root:
    python3 tools/hack/peak_trainers.py
"""
import json
import re

# name: (placeholder slot, template trainer for class/pic/name, items, team)
# team entries: (species, item, [moves]) - all Lv. 100
FR2 = ["ITEM_FULL_RESTORE"] * 2
FR4 = ["ITEM_FULL_RESTORE"] * 4
PEAK = {
    "BROCK": ("LEADER_ROXANNE", "LEADER_BROCK", FR2, [
        ("GOLEM", "CHOICE_BAND", ["EARTHQUAKE", "ROCK_SLIDE", "EXPLOSION", "DOUBLE_EDGE"]),
        ("OMASTAR", "MYSTIC_WATER", ["HYDRO_PUMP", "ICE_BEAM", "ANCIENT_POWER", "SPIKES"]),
        ("KABUTOPS", "SCOPE_LENS", ["ROCK_SLIDE", "WATERFALL", "BRICK_BREAK", "SWORDS_DANCE"]),
        ("AGGRON", "LEFTOVERS", ["IRON_TAIL", "ROCK_SLIDE", "EARTHQUAKE", "THUNDER_WAVE"]),
        ("STEELIX", "QUICK_CLAW", ["EARTHQUAKE", "IRON_TAIL", "ROCK_SLIDE", "EXPLOSION"]),
        ("TYRANITAR", "LEFTOVERS", ["DRAGON_DANCE", "ROCK_SLIDE", "EARTHQUAKE", "CRUNCH"])]),
    "MISTY": ("LEADER_BRAWLY", "LEADER_MISTY", FR2, [
        ("GOLDUCK", "MYSTIC_WATER", ["HYDRO_PUMP", "ICE_BEAM", "PSYCHIC", "CALM_MIND"]),
        ("LAPRAS", "LEFTOVERS", ["ICE_BEAM", "SURF", "THUNDERBOLT", "CONFUSE_RAY"]),
        ("VAPOREON", "LEFTOVERS", ["SURF", "ICE_BEAM", "WISH", "PROTECT"]),
        ("MILOTIC", "LEFTOVERS", ["SURF", "ICE_BEAM", "RECOVER", "TOXIC"]),
        ("GYARADOS", "LUM_BERRY", ["DRAGON_DANCE", "WATERFALL", "EARTHQUAKE", "DOUBLE_EDGE"]),
        ("STARMIE", "LEFTOVERS", ["SURF", "PSYCHIC", "THUNDERBOLT", "RECOVER"])]),
    "LT_SURGE": ("LEADER_WATTSON", "LEADER_LT_SURGE", FR2, [
        ("ELECTRODE", "MAGNET", ["THUNDERBOLT", "EXPLOSION", "THUNDER_WAVE", "TAUNT"]),
        ("MAGNETON", "LEFTOVERS", ["THUNDERBOLT", "THUNDER_WAVE", "SUBSTITUTE", "TOXIC"]),
        ("AMPHAROS", "LEFTOVERS", ["THUNDERBOLT", "FIRE_PUNCH", "THUNDER_WAVE", "LIGHT_SCREEN"]),
        ("MANECTRIC", "MAGNET", ["THUNDERBOLT", "FLAMETHROWER", "CRUNCH", "THUNDER_WAVE"]),
        ("JOLTEON", "MAGNET", ["THUNDERBOLT", "SHADOW_BALL", "THUNDER_WAVE", "AGILITY"]),
        ("RAICHU", "LEFTOVERS", ["THUNDERBOLT", "SURF", "BRICK_BREAK", "THUNDER_WAVE"])]),
    "ERIKA": ("LEADER_TATE_LIZA", "LEADER_ERIKA", FR2, [
        ("BRELOOM", "QUICK_CLAW", ["SPORE", "SKY_UPPERCUT", "MACH_PUNCH", "LEECH_SEED"]),
        ("VICTREEBEL", "MIRACLE_SEED", ["RAZOR_LEAF", "SLUDGE_BOMB", "SLEEP_POWDER", "SWORDS_DANCE"]),
        ("EXEGGUTOR", "LEFTOVERS", ["GIGA_DRAIN", "PSYCHIC", "SLEEP_POWDER", "EXPLOSION"]),
        ("LUDICOLO", "LEFTOVERS", ["SURF", "GIGA_DRAIN", "ICE_BEAM", "RAIN_DANCE"]),
        ("SCEPTILE", "MIRACLE_SEED", ["LEAF_BLADE", "EARTHQUAKE", "DRAGON_CLAW", "SWORDS_DANCE"]),
        ("VILEPLUME", "LEFTOVERS", ["GIGA_DRAIN", "SLUDGE_BOMB", "SLEEP_POWDER", "LEECH_SEED"])]),
    "KOGA": ("LEADER_FLANNERY", "LEADER_KOGA", FR2, [
        ("TENTACRUEL", "LEFTOVERS", ["SURF", "SLUDGE_BOMB", "ICE_BEAM", "RAPID_SPIN"]),
        ("VENOMOTH", "SILVER_POWDER", ["SLUDGE_BOMB", "PSYCHIC", "SILVER_WIND", "SLEEP_POWDER"]),
        ("MUK", "LEFTOVERS", ["SLUDGE_BOMB", "FIRE_PUNCH", "EXPLOSION", "CURSE"]),
        ("NIDOKING", "LEFTOVERS", ["EARTHQUAKE", "MEGAHORN", "ICE_BEAM", "THUNDERBOLT"]),
        ("GENGAR", "LEFTOVERS", ["SHADOW_BALL", "THUNDERBOLT", "HYPNOSIS", "DESTINY_BOND"]),
        ("WEEZING", "LEFTOVERS", ["SLUDGE_BOMB", "FIRE_BLAST", "WILL_O_WISP", "EXPLOSION"])]),
    "SABRINA": ("LEADER_NORMAN", "LEADER_SABRINA", FR2, [
        ("MR_MIME", "LEFTOVERS", ["PSYCHIC", "THUNDERBOLT", "CALM_MIND", "SUBSTITUTE"]),
        ("SLOWBRO", "LEFTOVERS", ["SURF", "PSYCHIC", "CALM_MIND", "REST"]),
        ("GARDEVOIR", "LEFTOVERS", ["PSYCHIC", "THUNDERBOLT", "CALM_MIND", "HYPNOSIS"]),
        ("METAGROSS", "CHOICE_BAND", ["METEOR_MASH", "EARTHQUAKE", "EXPLOSION", "ROCK_SLIDE"]),
        ("ESPEON", "LEFTOVERS", ["PSYCHIC", "SHADOW_BALL", "CALM_MIND", "MORNING_SUN"]),
        ("ALAKAZAM", "TWISTED_SPOON", ["PSYCHIC", "SHADOW_BALL", "CALM_MIND", "RECOVER"])]),
    "BLAINE": ("LEADER_WINONA", "LEADER_BLAINE", FR2, [
        ("RAPIDASH", "LEFTOVERS", ["FIRE_BLAST", "BOUNCE", "DOUBLE_EDGE", "HYPNOSIS"]),
        ("NINETALES", "LEFTOVERS", ["FLAMETHROWER", "EXTRASENSORY", "WILL_O_WISP", "CONFUSE_RAY"]),
        ("MAGMAR", "CHARCOAL", ["FIRE_BLAST", "THUNDERBOLT", "PSYCHIC", "CONFUSE_RAY"]),
        ("HOUNDOOM", "BLACK_GLASSES", ["FLAMETHROWER", "CRUNCH", "SLUDGE_BOMB", "ROAR"]),
        ("BLAZIKEN", "CHARCOAL", ["SKY_UPPERCUT", "BLAZE_KICK", "ROCK_SLIDE", "SWORDS_DANCE"]),
        ("ARCANINE", "LEFTOVERS", ["FIRE_BLAST", "EXTREME_SPEED", "CRUNCH", "ROAR"])]),
    "GIOVANNI": ("LEADER_WALLACE", "LEADER_GIOVANNI", FR2, [
        ("DUGTRIO", "CHOICE_BAND", ["EARTHQUAKE", "ROCK_SLIDE", "AERIAL_ACE", "SLASH"]),
        ("SANDSLASH", "QUICK_CLAW", ["EARTHQUAKE", "ROCK_SLIDE", "SWORDS_DANCE", "SLASH"]),
        ("MAROWAK", "THICK_CLUB", ["EARTHQUAKE", "ROCK_SLIDE", "DOUBLE_EDGE", "SWORDS_DANCE"]),
        ("NIDOQUEEN", "LEFTOVERS", ["EARTHQUAKE", "ICE_BEAM", "THUNDERBOLT", "SUPERPOWER"]),
        ("NIDOKING", "LEFTOVERS", ["EARTHQUAKE", "MEGAHORN", "ICE_BEAM", "THUNDERBOLT"]),
        ("RHYDON", "QUICK_CLAW", ["EARTHQUAKE", "ROCK_SLIDE", "MEGAHORN", "SWORDS_DANCE"])]),
    "LORELEI": ("ELITE_FOUR_SIDNEY", "ELITE_FOUR_LORELEI_2", FR2, [
        ("DEWGONG", "LEFTOVERS", ["ICE_BEAM", "SURF", "REST", "SLEEP_TALK"]),
        ("CLOYSTER", "NEVER_MELT_ICE", ["ICICLE_SPEAR", "SPIKES", "EXPLOSION", "RAPID_SPIN"]),
        ("JYNX", "NEVER_MELT_ICE", ["ICE_BEAM", "PSYCHIC", "LOVELY_KISS", "CALM_MIND"]),
        ("WALREIN", "LEFTOVERS", ["ICE_BEAM", "SURF", "BODY_SLAM", "REST"]),
        ("GLALIE", "QUICK_CLAW", ["EARTHQUAKE", "EXPLOSION", "CRUNCH", "ICE_BEAM"]),
        ("LAPRAS", "LEFTOVERS", ["ICE_BEAM", "SURF", "THUNDERBOLT", "CONFUSE_RAY"])]),
    "BRUNO": ("ELITE_FOUR_PHOEBE", "ELITE_FOUR_BRUNO_2", FR2, [
        ("HITMONTOP", "LEFTOVERS", ["HI_JUMP_KICK", "RAPID_SPIN", "EARTHQUAKE", "ROCK_SLIDE"]),
        ("HITMONCHAN", "BLACK_BELT", ["SKY_UPPERCUT", "ICE_PUNCH", "THUNDER_PUNCH", "FIRE_PUNCH"]),
        ("HITMONLEE", "SCOPE_LENS", ["HI_JUMP_KICK", "ROCK_SLIDE", "EARTHQUAKE", "BULK_UP"]),
        ("HARIYAMA", "LEFTOVERS", ["CROSS_CHOP", "EARTHQUAKE", "ROCK_SLIDE", "FAKE_OUT"]),
        ("HERACROSS", "CHOICE_BAND", ["MEGAHORN", "BRICK_BREAK", "ROCK_SLIDE", "EARTHQUAKE"]),
        ("MACHAMP", "LEFTOVERS", ["CROSS_CHOP", "ROCK_SLIDE", "EARTHQUAKE", "BULK_UP"])]),
    "AGATHA": ("ELITE_FOUR_GLACIA", "ELITE_FOUR_AGATHA_2", FR2, [
        ("SABLEYE", "LEFTOVERS", ["SHADOW_BALL", "KNOCK_OFF", "TOXIC", "PROTECT"]),
        ("MISDREAVUS", "LEFTOVERS", ["SHADOW_BALL", "THUNDERBOLT", "CALM_MIND", "PAIN_SPLIT"]),
        ("DUSCLOPS", "LEFTOVERS", ["SHADOW_PUNCH", "WILL_O_WISP", "CURSE", "REST"]),
        ("BANETTE", "SPELL_TAG", ["KNOCK_OFF", "FAINT_ATTACK", "WILL_O_WISP", "SHADOW_BALL"]),
        ("CROBAT", "SHARP_BEAK", ["AERIAL_ACE", "SLUDGE_BOMB", "CONFUSE_RAY", "TOXIC"]),
        ("GENGAR", "LEFTOVERS", ["SHADOW_BALL", "THUNDERBOLT", "PSYCHIC", "HYPNOSIS"])]),
    "LANCE": ("ELITE_FOUR_DRAKE", "ELITE_FOUR_LANCE_2", FR2, [
        ("KINGDRA", "MYSTIC_WATER", ["HYDRO_PUMP", "ICE_BEAM", "DRAGON_BREATH", "RAIN_DANCE"]),
        ("AERODACTYL", "SCOPE_LENS", ["ROCK_SLIDE", "EARTHQUAKE", "AERIAL_ACE", "DOUBLE_EDGE"]),
        ("ALTARIA", "LEFTOVERS", ["DRAGON_DANCE", "DRAGON_CLAW", "EARTHQUAKE", "FLAMETHROWER"]),
        ("FLYGON", "SOFT_SAND", ["EARTHQUAKE", "DRAGON_CLAW", "ROCK_SLIDE", "FIRE_BLAST"]),
        ("SALAMENCE", "CHOICE_BAND", ["DRAGON_CLAW", "EARTHQUAKE", "ROCK_SLIDE", "AERIAL_ACE"]),
        ("DRAGONITE", "LEFTOVERS", ["DRAGON_DANCE", "DRAGON_CLAW", "EARTHQUAKE", "FIRE_PUNCH"])]),
}
RIVAL_CORE = [
    ("PIDGEOT", "SHARP_BEAK", ["DOUBLE_EDGE", "AERIAL_ACE", "STEEL_WING", "QUICK_ATTACK"]),
    ("ALAKAZAM", "TWISTED_SPOON", ["PSYCHIC", "SHADOW_BALL", "CALM_MIND", "RECOVER"]),
    ("TYRANITAR", "LEFTOVERS", ["DRAGON_DANCE", "ROCK_SLIDE", "EARTHQUAKE", "CRUNCH"]),
]
EXEGGUTOR = ("EXEGGUTOR", "LEFTOVERS", ["GIGA_DRAIN", "PSYCHIC", "SLEEP_POWDER", "EXPLOSION"])
ARCANINE = ("ARCANINE", "CHARCOAL", ["FIRE_BLAST", "EXTREME_SPEED", "CRUNCH", "ROAR"])
GYARADOS = ("GYARADOS", "LEFTOVERS", ["DRAGON_DANCE", "WATERFALL", "EARTHQUAKE", "DOUBLE_EDGE"])
PEAK.update({
    "CHAMPION_SQUIRTLE": ("RS_CHAMPION", "CHAMPION_REMATCH_SQUIRTLE", FR4, RIVAL_CORE + [EXEGGUTOR, ARCANINE,
        ("BLASTOISE", "LEFTOVERS", ["HYDRO_PUMP", "ICE_BEAM", "EARTHQUAKE", "RAPID_SPIN"])]),
    "CHAMPION_BULBASAUR": ("WALLY", "CHAMPION_REMATCH_BULBASAUR", FR4, RIVAL_CORE + [GYARADOS, ARCANINE,
        ("VENUSAUR", "LEFTOVERS", ["GIGA_DRAIN", "SLUDGE_BOMB", "SLEEP_POWDER", "LEECH_SEED"])]),
    "CHAMPION_CHARMANDER": ("BRENDAN", "CHAMPION_REMATCH_CHARMANDER", FR4, RIVAL_CORE + [EXEGGUTOR, GYARADOS,
        ("CHARIZARD", "CHARCOAL", ["FIRE_BLAST", "DRAGON_BREATH", "SOLAR_BEAM", "SUNNY_DAY"])]),
})

GYMS = {  # leader: (gym map dir, TM flag line that precedes the post-battle text)
    "BROCK": ("PewterCity_Gym", "FLAG_GOT_TM39_FROM_BROCK"),
    "MISTY": ("CeruleanCity_Gym", "FLAG_GOT_TM03_FROM_MISTY"),
    "LT_SURGE": ("VermilionCity_Gym", "FLAG_GOT_TM34_FROM_SURGE"),
    "ERIKA": ("CeladonCity_Gym", "FLAG_GOT_TM19_FROM_ERIKA"),
    "KOGA": ("FuchsiaCity_Gym", "FLAG_GOT_TM06_FROM_KOGA"),
    "SABRINA": ("SaffronCity_Gym", "FLAG_GOT_TM04_FROM_SABRINA"),
    "BLAINE": ("CinnabarIsland_Gym", "FLAG_GOT_TM38_FROM_BLAINE"),
    "GIOVANNI": ("ViridianCity_Gym", "FLAG_GOT_TM26_FROM_GIOVANNI"),
}
LEAGUE_ROOMS = {"LORELEI": "LoreleisRoom", "BRUNO": "BrunosRoom", "AGATHA": "AgathasRoom", "LANCE": "LancesRoom"}
PEAK_LEAGUE_FLAG = "FLAG_HACK_PEAK_LEAGUE"


def camel(name):
    return "".join(w.title() for w in name.split("_"))


def sub(path, old, new, count=1):
    s = open(path).read()
    assert s.count(old) == count, (path, old[:70], s.count(old))
    open(path, "w").write(s.replace(old, new))


def check_constants():
    consts = set()
    for f in ("include/constants/species.h", "include/constants/moves.h", "include/constants/items.h"):
        consts |= set(re.findall(r"#define (\w+)", open(f).read()))
    for _, _, _, team in PEAK.values():
        assert len(team) == 6
        for sp, item, moves in team:
            for c in ["SPECIES_" + sp, "ITEM_" + item] + ["MOVE_" + m for m in moves]:
                assert c in consts, c


def write_constants():
    lines = ["", "// FireRed QoL+Hard: peak (post-game Lv. 100) trainers in unused RS slots"]
    lines += [f"#define TRAINER_PEAK_{n:<20} TRAINER_{slot}" for n, (slot, *_) in PEAK.items()]
    s = open("include/constants/opponents.h").read()
    i = s.rindex("#endif")
    open("include/constants/opponents.h", "w").write(s[:i] + "\n".join(lines) + "\n\n" + s[i:])
    sub("include/constants/trainers.h", "#define F_TRAINER_PARTY_HELD_ITEM      (1 << 1)",
        "#define F_TRAINER_PARTY_HELD_ITEM      (1 << 1)\n"
        "#define F_TRAINER_PARTY_PEAK           (1 << 7) // max IVs, matching nature, 252/252 EVs")
    sub("include/battle.h", "#define ITEM_CUSTOM_MOVES(party)",
        "#define PEAK_PARTY(party) { .ItemCustomMoves = party }, .partySize = ARRAY_COUNT(party), "
        ".partyFlags = F_TRAINER_PARTY_CUSTOM_MOVESET | F_TRAINER_PARTY_HELD_ITEM | F_TRAINER_PARTY_PEAK\n"
        "#define ITEM_CUSTOM_MOVES(party)")
    sub("include/constants/flags.h", "#define FLAG_HACK_LEGENDS_RELEASED",
        f"#define {PEAK_LEAGUE_FLAG:<32} (TRAINER_FLAGS_START + TRAINER_RS_COOLTRAINER_M)\n"
        "#define FLAG_HACK_LEGENDS_RELEASED")


def write_trainers():
    parties = ["", "// FireRed QoL+Hard: peak trainers (see tools/hack/peak_trainers.py)"]
    for name, (_, _, _, team) in PEAK.items():
        parties.append(f"static const struct TrainerMonItemCustomMoves sParty_Peak{camel(name)}[] = {{")
        for sp, item, moves in team:
            mv = ", ".join("MOVE_" + m for m in moves)
            parties += ["    {", "        .iv = 255,", "        .lvl = 100,", f"        .species = SPECIES_{sp},",
                        f"        .heldItem = ITEM_{item},", f"        .moves = {{{mv}}},", "    },"]
        parties.append("};")
    with open("src/data/trainer_parties.h", "a") as f:
        f.write("\n".join(parties) + "\n")

    p = "src/data/trainers.h"
    s = open(p).read()
    for name, (slot, template, items, _) in PEAK.items():
        tmpl = re.search(r"    \[TRAINER_%s\] = \{\n(.*?)\n    \},\n" % template, s, re.S).group(1)
        keep = [l for l in tmpl.split("\n") if re.match(r"\s*\.(trainerClass|encounterMusic_gender|trainerPic|trainerName) =", l)]
        body = "\n".join(keep + [
            f"        .items = {{{', '.join(items)}}},",
            "        .doubleBattle = FALSE,",
            "        .aiFlags = AI_SCRIPT_CHECK_BAD_MOVE | AI_SCRIPT_TRY_TO_FAINT | AI_SCRIPT_CHECK_VIABILITY,",
            f"        .party = PEAK_PARTY(sParty_Peak{camel(name)}),"])
        s, n = re.subn(r"    \[TRAINER_%s\] = \{\n.*?\n    \},\n" % slot,
                       lambda m: f"    [TRAINER_{slot}] = {{\n{body}\n    }},\n", s, count=1, flags=re.S)
        assert n == 1, slot
    open(p, "w").write(s)


def write_gym_scripts():
    for leader, (gym, tm_flag) in GYMS.items():
        p = f"data/maps/{gym}/scripts.inc"
        s = open(p).read()
        line = re.search(r"\tgoto_if_unset %s, \w+\n" % tm_flag, s).group(0)
        label = f"{gym}_EventScript_PeakRematch"
        sub(p, line, line + f"\tgoto_if_set FLAG_SYS_GAME_CLEAR, {label}\n")
        trainer = f"TRAINER_PEAK_{leader}"
        s = open(p).read() + f"""
@ FireRed QoL+Hard: post-game peak rematch
{label}::
	msgbox Hack_Text_PeakRematchOffer, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, Hack_EventScript_PeakRematchDeclined
	msgbox Hack_Text_PeakRematchStart
	cleartrainerflag {trainer}
	trainerbattle_no_intro {trainer}, Hack_Text_PeakRematchDefeat
	msgbox Hack_Text_PeakRematchAfter
	release
	end
"""
        open(p, "w").write(s)


def write_league_scripts():
    rooms = dict(LEAGUE_ROOMS, CHAMPION="ChampionsRoom")
    for member, room in rooms.items():
        p = f"data/maps/PokemonLeague_{room}/scripts.inc"
        prefix = f"PokemonLeague_{room}"
        old = (f"\tcall_if_unset FLAG_SYS_CAN_LINK_WITH_RS, {prefix}_EventScript_Battle\n"
               f"\tcall_if_set FLAG_SYS_CAN_LINK_WITH_RS, {prefix}_EventScript_Rematch\n")
        sub(p, old, f"\tcall {prefix}_EventScript_HackChooseBattle\n")
        if member == "CHAMPION":
            peak = "".join(f"\tcall_if_eq VAR_STARTER_MON, {v}, {prefix}_EventScript_HackPeak{camel(s)}\n"
                           for v, s in ((2, "SQUIRTLE"), (1, "BULBASAUR"), (0, "CHARMANDER")))
            peak += "\treturn\n"
            for s_ in ("SQUIRTLE", "BULBASAUR", "CHARMANDER"):
                peak += (f"\n{prefix}_EventScript_HackPeak{camel(s_)}::\n"
                         f"\tcleartrainerflag TRAINER_PEAK_CHAMPION_{s_}\n"
                         f"\ttrainerbattle_no_intro TRAINER_PEAK_CHAMPION_{s_}, {prefix}_Text_Defeat\n"
                         "\treturn\n")
                # Winning the peak battle must also stop the room's entry cutscene
                sub(p, f"\tgoto_if_defeated TRAINER_CHAMPION_REMATCH_{s_}, {prefix}_EventScript_StopSceneTrigger\n",
                    f"\tgoto_if_defeated TRAINER_CHAMPION_REMATCH_{s_}, {prefix}_EventScript_StopSceneTrigger\n"
                    f"\tgoto_if_defeated TRAINER_PEAK_CHAMPION_{s_}, {prefix}_EventScript_StopSceneTrigger\n")
        else:
            peak = (f"\tcleartrainerflag TRAINER_PEAK_{member}\n"
                    f"\ttrainerbattle_no_intro TRAINER_PEAK_{member}, {prefix}_Text_Defeat\n"
                    "\treturn\n")
        s = open(p).read() + f"""
@ FireRed QoL+Hard: round 3 (peak) when chosen at the Indigo Plateau
{prefix}_EventScript_HackChooseBattle::
	goto_if_set {PEAK_LEAGUE_FLAG}, {prefix}_EventScript_HackPeakBattle
	call_if_unset FLAG_SYS_CAN_LINK_WITH_RS, {prefix}_EventScript_Battle
	call_if_set FLAG_SYS_CAN_LINK_WITH_RS, {prefix}_EventScript_Rematch
	return

{prefix}_EventScript_HackPeakBattle::
{peak}"""
        open(p, "w").write(s)
    # Peak champion flags are reset with the others at every Hall of Fame entry
    sub("data/scripts/hall_of_fame.inc", "\tcleartrainerflag TRAINER_CHAMPION_REMATCH_CHARMANDER\n",
        "\tcleartrainerflag TRAINER_CHAMPION_REMATCH_CHARMANDER\n"
        "\tcleartrainerflag TRAINER_PEAK_CHAMPION_SQUIRTLE\n"
        "\tcleartrainerflag TRAINER_PEAK_CHAMPION_BULBASAUR\n"
        "\tcleartrainerflag TRAINER_PEAK_CHAMPION_CHARMANDER\n")


def write_official():
    p = "data/maps/IndigoPlateau_PokemonCenter_1F/map.json"
    m = json.load(open(p))
    m["object_events"].append({
        "type": "object", "graphics_id": "OBJ_EVENT_GFX_GENTLEMAN", "x": 7, "y": 4, "elevation": 3,
        "movement_type": "MOVEMENT_TYPE_FACE_DOWN", "movement_range_x": 1, "movement_range_y": 1,
        "trainer_type": "TRAINER_TYPE_NONE", "trainer_sight_or_berry_tree_id": "0",
        "script": "IndigoPlateau_PokemonCenter_1F_EventScript_PeakOfficial", "flag": "0"})
    with open(p, "w") as f:
        json.dump(m, f, indent=2)
        f.write("\n")
    p = "data/maps/IndigoPlateau_PokemonCenter_1F/scripts.inc"
    s = open(p).read() + f"""
@ FireRed QoL+Hard: toggles the peak (round 3) Elite Four challenge
IndigoPlateau_PokemonCenter_1F_EventScript_PeakOfficial::
	lock
	faceplayer
	goto_if_unset FLAG_SYS_GAME_CLEAR, IndigoPlateau_PokemonCenter_1F_EventScript_PeakNotChampion
	goto_if_set {PEAK_LEAGUE_FLAG}, IndigoPlateau_PokemonCenter_1F_EventScript_PeakIsOn
	msgbox Hack_Text_PeakOfficialOffOffer, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, IndigoPlateau_PokemonCenter_1F_EventScript_PeakOfficialDone
	setflag {PEAK_LEAGUE_FLAG}
	msgbox Hack_Text_PeakOfficialNowOn
	release
	end

IndigoPlateau_PokemonCenter_1F_EventScript_PeakIsOn::
	msgbox Hack_Text_PeakOfficialOnOffer, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, IndigoPlateau_PokemonCenter_1F_EventScript_PeakOfficialDone
	clearflag {PEAK_LEAGUE_FLAG}
	msgbox Hack_Text_PeakOfficialNowOff
	release
	end

IndigoPlateau_PokemonCenter_1F_EventScript_PeakNotChampion::
	msgbox Hack_Text_PeakOfficialNotChampion
	release
	end

IndigoPlateau_PokemonCenter_1F_EventScript_PeakOfficialDone::
	msgbox Hack_Text_PeakOfficialDone
	release
	end
"""
    open(p, "w").write(s)


def write_texts():
    open("data/scripts/hack_peak_trainers.inc", "w").write("""@ FireRed QoL+Hard: shared peak trainer texts (generated by tools/hack/peak_trainers.py)

Hack_EventScript_PeakRematchDeclined::
	msgbox Hack_Text_PeakRematchDeclined
	release
	end

Hack_Text_PeakRematchOffer::
	.string "So you've become the CHAMPION!\\p"
	.string "Want to face my team at its absolute\\n"
	.string "peak? Six POKéMON at Lv. 100,\\l"
	.string "and I won't hold anything back!$"

Hack_Text_PeakRematchStart::
	.string "Then show me what a CHAMPION\\n"
	.string "can do!$"

Hack_Text_PeakRematchDefeat::
	.string "Incredible…\\n"
	.string "You really are the CHAMPION.$"

Hack_Text_PeakRematchAfter::
	.string "Come back any time.\\n"
	.string "I'll be ready for another round!$"

Hack_Text_PeakRematchDeclined::
	.string "Whenever you're ready, CHAMPION.$"

Hack_Text_PeakOfficialNotChampion::
	.string "I'm a POKéMON LEAGUE official.\\p"
	.string "Once you become CHAMPION, I can\\n"
	.string "arrange a very special challenge.$"

Hack_Text_PeakOfficialOffOffer::
	.string "Welcome back, CHAMPION!\\p"
	.string "I can arrange the PEAK challenge:\\n"
	.string "the ELITE FOUR and CHAMPION with\\l"
	.string "six Lv. 100 POKéMON each.\\p"
	.string "Would you like to take it on?$"

Hack_Text_PeakOfficialOnOffer::
	.string "The PEAK challenge is currently on.\\p"
	.string "Would you like to go back to the\\n"
	.string "regular ELITE FOUR?$"

Hack_Text_PeakOfficialNowOn::
	.string "The PEAK challenge is on!\\n"
	.string "Good luck, CHAMPION!$"

Hack_Text_PeakOfficialNowOff::
	.string "The regular ELITE FOUR are\\n"
	.string "waiting for you.$"

Hack_Text_PeakOfficialDone::
	.string "Talk to me any time to switch.$"
""")
    sub("data/event_scripts.s", '\t.include "data/scripts/hack_legendaries.inc"\n',
        '\t.include "data/scripts/hack_legendaries.inc"\n\t.include "data/scripts/hack_peak_trainers.inc"\n')


check_constants()
write_constants()
write_trainers()
write_gym_scripts()
write_league_scripts()
write_official()
write_texts()
print(f"{len(PEAK)} peak trainers, {len(GYMS)} gym rematches, league round 3 added")
