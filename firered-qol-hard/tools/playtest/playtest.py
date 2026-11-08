#!/usr/bin/env python3
"""Automated playtest: milestone checks from a new game to the post-game.

Each check builds a throwaway ROM that starts a new game at a set point (a
warp plus a party), plays the real game scripts and battles with button
presses, then reads the save block to confirm the milestone happened:

  boot        new game -> challenge menu in your room -> START ADVENTURE
  wild_exp    a wild battle gives Exp. and stops at the level cap (16)
  trainer     a Viridian Forest trainer battle is won and recorded
  nuzlocke    Nuzlocke: the first catch in an area works, the second is refused
  gym_double  a gym double battle (Psychic Johan) is won
  tower_*     Trainer Tower 1F in the Single, Double and Knockout challenges:
              the foes are that floor's Pokemon, everyone battles at Lv. 50, and
              the player's Pokemon are back to their real level afterwards
  misty, surge  their real gym scripts: battle won, badge awarded
  berry_shop  buy a Cheri Berry at the Celadon 2F berry stand (it lands in the Berry Pouch)
  held_item_shop  buy Leftovers at the post-game Trainer Tower lobby shop
  peak_reward a peak Gym Leader win gives an item from the reward pool
  tower_prize the Trainer Tower prize is given again on a second clear
  league_reward  a peak Champion win gives an item from the League reward pool
  tower_record   a new Trainer Tower record time gives the bonus prize
  trader      the Trainer Tower lobby trader swaps 3 Star Pieces for a Master Ball
  nuzlocke_blackout    Nuzlocke: losing an ordinary trainer battle ends the run
  nuzlocke_exhibition  Nuzlocke: losing to a peak trainer doesn't (exhibition battle)
  exp_share   Party Exp. Share: the Pokemon that didn't battle levels up too
  vr_rematch  the VS Seeker in Victory Road: Naomi's rematch team (Lv. 56 Persian)
  brock       Brock's real gym script: battle won, Boulder Badge awarded

A check fails if its state isn't reached, which also catches crashes and
softlocks. Screenshots of every check go to the output directory.

usage: python3 tools/hack/playtest/playtest.py [check ...] [--out DIR]
needs: a built tree (make), git, and the harness built from harness.c:
  gcc -O2 -w -o tools/hack/playtest/harness tools/hack/playtest/harness.c -lmgba
The scenario edits to the source are always reverted (git checkout).
"""
import json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
HARNESS = os.path.join(HERE, "harness")


def read(p):
    return open(os.path.join(R, p), encoding="utf-8").read()


# ---------------------------------------------------------------- constants
DEFS = {}
for f in ("include/constants/flags.h", "include/constants/vars.h", "include/constants/opponents.h"):
    for name, val in re.findall(r"#define (\w+)\s+([^/\n]+)", read(f)):
        DEFS[name] = val.strip()


def const(expr, depth=0):
    """Evaluate a constant name or expression from the headers."""
    if depth > 20:
        raise ValueError(expr)
    expr = DEFS.get(expr, expr)
    expr = re.sub(r"\b[A-Za-z_]\w*\b", lambda m: str(const(m.group(0), depth + 1)) if m.group(0) in DEFS else m.group(0), expr)
    return int(eval(expr, {}))


SB1_FLAGS, SB1_VARS, SB1_ITEMS, SB1_BAG, SB1_BALLS = 0x0EE0, 0x1000, 0x0310, 0x054C, 0x0430  # flags, vars, Items, Berry Pouch, Poke Balls
SYMS = {}
for addr, name in re.findall(r"^\s+0x([0-9a-f]{8})\s+(g\w+)(?:\s*=\s*\.)?$", read("pokefirered.map"), re.M):
    SYMS[name] = int(addr, 16)

# ---------------------------------------------------------------- scenarios
INTRO = "wait 2100\npress S 6\nwait 120\n" + ("press A 4\nwait 20\n" * 5) * 18 + "wait 200\n"
GENTLEMAN = ("data/maps/ViridianCity_PokemonCenter_1F/scripts.inc",
             "\tmsgbox ViridianCity_PokemonCenter_1F_Text_FeelFreeToUsePC, MSGBOX_NPC\n\tend\n\n"
             "ViridianCity_PokemonCenter_1F_EventScript_Youngster")
VIRIDIAN = ["MAP_VIRIDIAN_CITY_POKEMON_CENTER_1F", 13, 5]


def gentleman(script):
    return [GENTLEMAN[0], GENTLEMAN[1], script + "\n\tend\n\nViridianCity_PokemonCenter_1F_EventScript_Youngster"]


def mash(n, wait=120):
    return "".join(f"press A 6\nwait {wait}\n" for _ in range(n))


TALK_LEFT = "wait 120\npress L 2\nwait 30\npress A 6\nwait 300\n"
CHECKS = {
    "boot": dict(
        scenario=None,
        body="wait 200\n" + mash(2) + "".join("press D 6\nwait 15\n" for _ in range(5)) + "press A 6\nwait 60\n" + mash(10),
        expect=[("var", "VAR_MAP_SCENE_PALLET_TOWN_PLAYERS_HOUSE_2F", 2)]),
    "wild_exp": dict(
        scenario={"party": [["RATTATA", 14, ["HYPER_FANG"]]], "set": ["FLAG_HACK_LEVEL_CAP"], "warp": VIRIDIAN,
                  "patch": [gentleman("\tsetwildbattle SPECIES_RATTATA, 5\n\tdowildbattle"),
                            ["src/battle_script_commands.c", "expYield * gBattleMons[gBattlerFainted].level / 5;",
                             "expYield * gBattleMons[gBattlerFainted].level * 30;"]]},
        body=TALK_LEFT + mash(30, 90),
        expect=[("level", 0, 16)]),
    "trainer": dict(
        scenario={"party": [["PIDGEOT", 30, ["WING_ATTACK"]]], "warp": VIRIDIAN,
                  "patch": [gentleman("\ttrainerbattle_no_intro TRAINER_BUG_CATCHER_RICK, ViridianCity_PokemonCenter_1F_Text_FeelFreeToUsePC")]},
        body=TALK_LEFT + mash(40, 90),
        expect=[("flag", "TRAINER_FLAGS_START + TRAINER_BUG_CATCHER_RICK", 1)]),
    "nuzlocke": dict(
        scenario={"party": [["MEWTWO", 50, ["CONFUSION"]]], "items": [["MASTER_BALL", 3]],
                  "set": ["FLAG_HACK_NUZLOCKE", "FLAG_SYS_POKEDEX_GET"], "warp": VIRIDIAN,
                  "patch": [gentleman("\tsetwildbattle SPECIES_CATERPIE, 3\n\tdowildbattle"),
                            ["src/scrcmd.c", "    StartScriptedWildBattle();\n    ScriptContext_Stop();",
                             "    { extern bool8 gHackRandomEncounter; gHackRandomEncounter = TRUE; }\n"
                             "    StartScriptedWildBattle();\n    ScriptContext_Stop();"]]},
        # Battle 1: Bag -> Poke Balls -> Master Ball -> Use. Battle 2: the same, refused, then run.
        body=(TALK_LEFT + "press A 6\nwait 200\npress R 6\nwait 30\npress A 6\nwait 150\npress R 6\nwait 40\npress R 6\n"
              "wait 40\npress A 6\nwait 40\npress A 6\nwait 400\n" + "press B 6\nwait 120\n" * 10 +
              TALK_LEFT + "press A 6\nwait 200\npress R 6\nwait 30\npress A 6\nwait 150\npress A 6\nwait 40\n"
              "press A 6\nwait 150\npress A 6\nwait 60\npress B 6\nwait 60\npress B 6\nwait 120\n"
              "press D 6\nwait 20\npress R 6\nwait 20\npress A 6\nwait 300\n" + mash(4)),
        expect=[("party_count", None, 2)]),
    "gym_double": dict(
        scenario={"party": [["MEWTWO", 60, ["SHADOW_BALL"]], ["SNORLAX", 60, ["BODY_SLAM"]]], "warp": VIRIDIAN,
                  "patch": [gentleman("\ttrainerbattle_double TRAINER_PSYCHIC_JOHAN, ViridianCity_PokemonCenter_1F_Text_FeelFreeToUsePC, "
                                      "ViridianCity_PokemonCenter_1F_Text_FeelFreeToUsePC, Hack_Text_GymDoubleNotEnough")]},
        body=TALK_LEFT + mash(80, 90),
        expect=[("flag", "TRAINER_FLAGS_START + TRAINER_PSYCHIC_JOHAN", 1)]),
    # Trainer Tower: the challenge is started in the scenario setup, then the
    # player steps onto the floor's battle trigger on 1F. Mid-battle, the foes
    # must be real species from that floor's data, and every battler (the
    # player's Lv. 100 Mewtwo too) must be Lv. 50 under the tower's Lv. 50 rule.
    # After the battle the player's Pokemon are back to Lv. 100.
    "tower_single": dict(
        scenario={"party": [["MEWTWO", 100, ["PSYCHIC"]]], "tower": 0,
                  "warp": ["MAP_TRAINER_TOWER_1F", 10, 14]},
        body="wait 120\npress U 12\nwait 300\n" + mash(12, 90) + "BATTLE_PEEK\n" + mash(60, 90),
        expect=[("tower_foes", 0, 1), ("level", 0, 100)]),
    "tower_double": dict(
        scenario={"party": [["MEWTWO", 100, ["PSYCHIC"]]] * 2, "tower": 1,
                  "warp": ["MAP_TRAINER_TOWER_1F", 9, 14]},
        body="wait 120\npress U 12\nwait 300\n" + mash(12, 90) + "BATTLE_PEEK\n" + mash(60, 90),
        expect=[("tower_foes", 1, 2), ("level", 0, 100), ("level", 1, 100)]),
    "tower_knockout": dict(
        scenario={"party": [["MEWTWO", 100, ["PSYCHIC"]]], "tower": 2,
                  "warp": ["MAP_TRAINER_TOWER_1F", 10, 14]},
        body="wait 120\npress U 12\nwait 300\n" + mash(12, 90) + "BATTLE_PEEK\n" + mash(60, 90),
        expect=[("tower_foes", 2, 1), ("level", 0, 100)]),
    "misty": dict(
        scenario={"party": [["VENUSAUR", 40, ["GIGA_DRAIN"]]] * 2,
                  "set": ["FLAG_SYS_POKEDEX_GET", "FLAG_BADGE01_GET", "TRAINER_FLAGS_START + TRAINER_SWIMMER_MALE_LUIS",
                          "TRAINER_FLAGS_START + TRAINER_PICNICKER_DIANA"],
                  "warp": ["MAP_CERULEAN_CITY_GYM", 8, 7]},
        body="wait 120\npress U 2\nwait 30\npress A 6\nwait 200\n" + mash(90, 90),
        expect=[("flag", "FLAG_BADGE02_GET", 1)]),
    "surge": dict(
        scenario={"party": [["GOLEM", 45, ["EARTHQUAKE"]]] * 2,
                  "set": ["FLAG_SYS_POKEDEX_GET", "FLAG_BADGE01_GET", "FLAG_BADGE02_GET"],
                  "warp": ["MAP_VERMILION_CITY_GYM", 5, 3]},
        body="wait 120\npress U 2\nwait 30\npress A 6\nwait 200\n" + mash(90, 90),
        expect=[("flag", "FLAG_BADGE03_GET", 1)]),
    "berry_shop": dict(
        # Celadon 2F berry stand: Buy -> Cheri Berry -> x1 -> yes.
        scenario={"party": [["PIDGEY", 10]], "warp": ["MAP_CELADON_CITY_DEPARTMENT_STORE_2F", 3, 7]},
        body=("wait 150\npress L 2\nwait 30\npress A 6\nwait 120\npress A 6\nwait 120\npress A 6\nwait 60\n"
              "press A 6\nwait 60\npress A 6\nwait 90\npress A 6\nwait 90\npress B 6\nwait 60\npress B 6\nwait 90\n" + mash(3)),
        expect=[("bag_has", "ITEM_CHERI_BERRY", 1)]),
    "held_item_shop": dict(
        # Trainer Tower lobby shop (post-game): buy Leftovers, the first held item after the 9 consumables.
        scenario={"party": [["PIDGEY", 10]], "warp": ["MAP_TRAINER_TOWER_LOBBY", 14, 10],
                  "patch": [["src/new_game.c", "(void)slot;", "(void)slot; SetMoney(&gSaveBlock1Ptr->money, 50000);"]]},
        body=("wait 150\npress U 2\nwait 30\npress A 6\nwait 120\npress A 6\nwait 120\n" + "press D 6\nwait 10\n" * 9 +
              "press A 6\nwait 60\npress A 6\nwait 60\npress A 6\nwait 90\npress A 6\nwait 90\npress B 6\nwait 60\npress B 6\nwait 90\n" + mash(3)),
        expect=[("bag_has", "ITEM_LEFTOVERS", 1)]),
    "peak_reward": dict(
        # The reward a peak Gym Leader gives after a win (the script the gyms call).
        scenario={"party": [["PIDGEY", 10]], "warp": VIRIDIAN,
                  "patch": [gentleman("\tlock\n\tcall Hack_EventScript_PeakReward\n\trelease")]},
        body=TALK_LEFT + mash(8),
        expect=[("bag_any", ["ITEM_NUGGET", "ITEM_PP_UP", "ITEM_PP_MAX", "ITEM_STAR_PIECE"], 1)]),
    "tower_prize": dict(
        # The Trainer Tower prize, twice: every clear now gives one.
        scenario={"party": [["PIDGEY", 10]], "warp": VIRIDIAN,
                  "patch": [gentleman("\tlock\n\tsetvar VAR_0x8005, 0\n\tttower_startchallenge\n\tttower_giveprize\n"
                                      "\tttower_startchallenge\n\tttower_giveprize\n\tcopyvar VAR_0x402A, VAR_RESULT\n\trelease")]},
        body=TALK_LEFT + mash(4),
        expect=[("bag_any", ["ITEM_UP_GRADE", "ITEM_NUGGET", "ITEM_PP_UP", "ITEM_PP_MAX", "ITEM_BIG_PEARL", "ITEM_STAR_PIECE"], 1),
                ("var", "VAR_0x402A", 0)]),
    "league_reward": dict(
        # The reward for a peak (round 3) Champion win.
        scenario={"party": [["PIDGEY", 10]], "warp": VIRIDIAN,
                  "patch": [gentleman("\tlock\n\tcall Hack_EventScript_PeakLeagueReward\n\trelease")]},
        body=TALK_LEFT + mash(8),
        expect=[("bag_any", ["ITEM_MASTER_BALL", "ITEM_PP_MAX", "ITEM_STAR_PIECE", "ITEM_NUGGET"], 1)]),
    "tower_record": dict(
        # A new Trainer Tower record time: the roof script's record check gives the bonus prize.
        scenario={"party": [["PIDGEY", 10]], "warp": VIRIDIAN,
                  "patch": [gentleman("\tlock\n\tsetvar VAR_0x8005, 0\n\tttower_startchallenge\n"
                                      "\tcall TrainerTower_Roof_EventScript_CheckFinalTime")]},
        body=TALK_LEFT + mash(10),
        expect=[("bag_any", ["ITEM_MASTER_BALL", "ITEM_RARE_CANDY", "ITEM_STAR_PIECE", "ITEM_PP_MAX"], 1)]),
    "trader": dict(
        # The Trainer Tower lobby trader: 3 Star Pieces for a Master Ball.
        scenario={"party": [["PIDGEY", 10]], "items": [["STAR_PIECE", 3]], "warp": ["MAP_TRAINER_TOWER_LOBBY", 3, 12]},
        body=TALK_LEFT + mash(9) + "press B 6\nwait 90\npress A 6\nwait 120\n",
        expect=[("bag_has", "ITEM_MASTER_BALL", 1), ("bag_has", "ITEM_STAR_PIECE", 0)]),
    "nuzlocke_blackout": dict(
        # Nuzlocke: losing an ordinary trainer battle ends the run.
        scenario={"party": [["MAGIKARP", 5, ["SPLASH"]]], "set": ["FLAG_HACK_NUZLOCKE", "FLAG_SYS_POKEDEX_GET"], "warp": VIRIDIAN,
                  "patch": [gentleman("\ttrainerbattle_no_intro TRAINER_LEADER_BROCK, ViridianCity_PokemonCenter_1F_Text_FeelFreeToUsePC")]},
        body=TALK_LEFT + mash(40, 90),
        expect=[("flag", "FLAG_HACK_NUZLOCKE", 0)]),  # the "run over" flag is cleared once its message shows
    "nuzlocke_exhibition": dict(
        # Nuzlocke: losing to a peak trainer (an exhibition battle) doesn't count.
        scenario={"party": [["MAGIKARP", 5, ["SPLASH"]]], "set": ["FLAG_HACK_NUZLOCKE", "FLAG_SYS_POKEDEX_GET"], "warp": VIRIDIAN,
                  "patch": [gentleman("\ttrainerbattle_no_intro TRAINER_PEAK_BROCK, ViridianCity_PokemonCenter_1F_Text_FeelFreeToUsePC")]},
        body=TALK_LEFT + mash(40, 90),
        expect=[("flag", "FLAG_HACK_NUZLOCKE", 1), ("alive", 0, 1)]),
    "exp_share": dict(
        # Party Exp. Share: the Pokemon that didn't battle still levels up.
        scenario={"party": [["PIDGEOT", 40, ["WING_ATTACK"]], ["RATTATA", 5, ["TACKLE"]]],
                  "set": ["FLAG_HACK_PARTY_EXP_SHARE"], "warp": VIRIDIAN,
                  "patch": [gentleman("\tsetwildbattle SPECIES_RATTATA, 20\n\tdowildbattle")]},
        body=TALK_LEFT + mash(30, 90),
        expect=[("level_min", 1, 6), ("level", 0, 40)]),
    "vr_rematch": dict(
        # The real VS Seeker flow in Victory Road: use it, then challenge Naomi.
        scenario={"party": [["MEWTWO", 70, ["PSYCHIC"]]], "items": [["VS_SEEKER", 1]],
                  "set": ["FLAG_GOT_VS_SEEKER", "FLAG_SYS_POKEDEX_GET", "TRAINER_FLAGS_START + TRAINER_COOLTRAINER_NAOMI"],
                  "warp": ["MAP_VICTORY_ROAD_1F", 14, 8],
                  "patch": [["src/new_game.c", "(void)slot;", "(void)slot; gSaveBlock1Ptr->trainerRematchStepCounter = 100;"]]},
        body=("wait 150\npress S 6\nwait 40\npress D 6\nwait 10\npress D 6\nwait 10\npress A 6\nwait 150\n"
              "press R 6\nwait 40\npress A 6\nwait 40\npress A 6\nwait 400\npress A 6\nwait 120\n"
              "press U 6\nwait 30\npress U 12\nwait 60\npress A 6\nwait 150\n" + mash(6, 120) + "BATTLE_PEEK\n" + mash(10)),
        expect=[("foe", "SPECIES_PERSIAN", 56)]),
    "brock": dict(
        scenario={"party": [["BLASTOISE", 36, ["SURF"]]], "set": ["FLAG_SYS_POKEDEX_GET"],
                  "warp": ["MAP_PEWTER_CITY_GYM", 6, 6]},
        body="wait 120\npress U 2\nwait 30\npress A 6\nwait 200\n" + mash(70, 90),
        expect=[("flag", "FLAG_BADGE01_GET", 1), ("flag", "FLAG_DEFEATED_BROCK", 1)]),
}


def build(name, cfg, workdir):
    """Build a scenario ROM (or the plain ROM) and return its path."""
    rom = os.path.join(workdir, name + ".gba")
    if cfg is None:
        subprocess.run(["make", "-j8"], cwd=R, check=True, capture_output=True)
        shutil.copy(os.path.join(R, "pokefirered.gba"), rom)
        return rom
    code = ["    { // PLAYTEST SCENARIO", "        u16 mv; u8 slot = 0;"]
    for i, p in enumerate(cfg.get("party", [])):
        code.append(f"        ScriptGiveMon(SPECIES_{p[0]}, {p[1]}, 0, 0, 0, 0);")
        for j, m in enumerate(p[2] if len(p) > 2 else []):
            code.append(f"        mv = MOVE_{m}; SetMonData(&gPlayerParty[{i}], MON_DATA_MOVE1 + {j}, &mv); "
                        f"SetMonData(&gPlayerParty[{i}], MON_DATA_PP1 + {j}, &gBattleMoves[mv].pp);")
    for it, n in cfg.get("items", []):
        code.append(f"        AddBagItem(ITEM_{it}, {n});")
    code.append("        FlagSet(FLAG_SYS_POKEMON_GET);")
    code += [f"        FlagSet({f});" for f in cfg.get("set", [])]
    if "tower" in cfg:
        code.append(f"        gSpecialVar_0x8005 = {cfg['tower']}; gSpecialVar_0x8004 = TRAINER_TOWER_FUNC_START_CHALLENGE; "
                    "CallTrainerTowerFunc(); VarSet(VAR_MAP_SCENE_TRAINER_TOWER, 1);")
    m, x, y = cfg["warp"]
    code.append(f"        SetWarpDestination(MAP_GROUP({m}), MAP_NUM({m}), -1, {x}, {y}); WarpIntoMap();")
    code += ["        (void)slot;", "    }"]
    touched = {"src/new_game.c": None}
    for f, _, _ in cfg.get("patch", []):
        touched[f] = None
    dirty = subprocess.run(["git", "status", "--porcelain", "--"] + list(touched), cwd=R, capture_output=True, text=True).stdout
    if dirty.strip():
        sys.exit("Commit or stash your changes to these files first:\n" + dirty)
    try:
        p = os.path.join(R, "src/new_game.c")
        s = open(p).read()
        s = s.replace('#include "overworld.h"', '#include "overworld.h"\n#include "script_pokemon_util.h"\n#include "pokemon.h"\n'
                      '#include "constants/items.h"\n#include "constants/moves.h"\n#include "constants/opponents.h"\n'
                      '#include "constants/flags.h"\n#include "constants/vars.h"\n#include "constants/trainer_tower.h"\n'
                      'void CallTrainerTowerFunc(void);', 1)
        s = s.replace("    ResetTrainerTowerResults();\n}", "    ResetTrainerTowerResults();\n" + "\n".join(code) + "\n}", 1)
        open(p, "w").write(s)
        for f, old, new in cfg.get("patch", []):
            q = os.path.join(R, f)
            t = open(q).read()
            assert old in t, (f, old)
            open(q, "w").write(t.replace(old, new))
        r = subprocess.run(["make", "-j8"], cwd=R, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError("build failed:\n" + "\n".join(l for l in (r.stdout + r.stderr).splitlines() if "error" in l.lower()))
        shutil.copy(os.path.join(R, "pokefirered.gba"), rom)
    finally:
        subprocess.run(["git", "checkout", "--"] + list(touched), cwd=R, capture_output=True)
    return rom


ITEMS = {n: int(v) for n, v in re.findall(r"#define (ITEM_\w+)\s+(\d+)\n", read("include/constants/items.h"))}
for n, v in re.findall(r"#define (ITEM_\w+)\s+(ITEM_\w+)", read("include/constants/items.h")):
    if v in ITEMS:
        ITEMS[n] = ITEMS[v]


def species_id(name, depth=0):
    v = dict(re.findall(r"#define (SPECIES_\w+)\s+([^/\n]+)", read("include/constants/species.h")))[name].strip()
    return int(v, 0) if re.fullmatch(r"(0x[0-9A-Fa-f]+|\d+)", v) else species_id(v, depth + 1)


def tower_floor1_species(mode):
    """Species in the first floor of a Trainer Tower challenge (all its trainers)."""
    text = read("src/trainer_tower_sets.c")
    table = text[text.rindex("[CHALLENGE_TYPE_SINGLE] = {"):]
    names = re.findall(r"&(\w+)", re.findall(r"\[CHALLENGE_TYPE_\w+\] = \{(.*?)\}", table, re.S)[mode])
    body = re.search(r"static const struct TrainerTowerFloor %s = \{(.*?)\n\};" % names[0], text, re.S).group(1)
    species = read("include/constants/species.h")
    ids = {}
    for n, v in re.findall(r"#define (SPECIES_\w+)\s+([^/\n]+)", species):
        ids[n] = v.strip()

    def num(n, d=0):
        v = ids[n]
        return int(v, 0) if re.fullmatch(r"(0x[0-9A-Fa-f]+|\d+)", v) else num(v, d + 1)
    return {num(sp) for sp in re.findall(r"\.species = (SPECIES_\w+)", body)}


def run(rom, body, outdir, name):
    """Run the scenario. Returns a dict of reads: flags, vars, count, party,
    and battle (gBattleMons, if the body asked for it with BATTLE_PEEK)."""
    ptr = SYMS["gSaveBlock1Ptr"]
    body = body.replace("BATTLE_PEEK", f"peek {SYMS['gBattleMons']:x} {4 * 0x58}")
    script = INTRO + body + f"shot {name}_end\n"
    script += f"peekp {ptr:x} {SB1_FLAGS:x} 288\npeekp {ptr:x} {SB1_VARS:x} 512\n"
    script += f"peek {SYMS['gPlayerPartyCount']:x} 1\npeek {SYMS['gPlayerParty']:x} 600\n"
    script += f"peekp {ptr:x} {SB1_BAG:x} 172\npeekp {ptr:x} {SB1_ITEMS:x} 168\npeekp {ptr:x} {SB1_BALLS:x} 52\n"
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, name + ".txt")
    open(path, "w").write(script)
    out = subprocess.run([HARNESS, rom, path], cwd=outdir, capture_output=True, text=True, timeout=1200).stdout
    reads = {}
    for addr, data in re.findall(r"^PEEKP? (\S+) ([0-9a-f]*)$", out, re.M):
        reads[addr] = bytes.fromhex(data)
    keyed = {"flags": reads.get(f"{ptr:08x}+{SB1_FLAGS:x}"), "vars": reads.get(f"{ptr:08x}+{SB1_VARS:x}"),
             "count": reads.get(f"{SYMS['gPlayerPartyCount']:08x}"), "party": reads.get(f"{SYMS['gPlayerParty']:08x}"),
             "battle": reads.get(f"{SYMS['gBattleMons']:08x}"), "bag": (reads.get(f"{ptr:08x}+{SB1_BAG:x}") or b"") + (reads.get(f"{ptr:08x}+{SB1_ITEMS:x}") or b"")
             + (reads.get(f"{ptr:08x}+{SB1_BALLS:x}") or b"")}
    return keyed


def check(name, spec, workdir, outdir):
    rom = build(name, spec["scenario"], workdir)
    r = run(rom, spec["body"], outdir, name)
    fails = []
    for kind, what, want in spec["expect"]:
        if kind == "flag":
            n = const(what) if not what.isdigit() else int(what)
            got = (r["flags"][n // 8] >> (n % 8)) & 1
        elif kind == "var":
            n = const(what) - 0x4000
            got = r["vars"][2 * n] | (r["vars"][2 * n + 1] << 8)
        elif kind == "level":
            got = r["party"][100 * what + 0x54]  # struct Pokemon is 100 bytes; level at 0x54
        elif kind == "level_min":
            lvl = r["party"][100 * what + 0x54]
            got = want if lvl >= want else lvl
        elif kind == "alive":
            got = int((r["party"][100 * what + 0x56] | (r["party"][100 * what + 0x57] << 8)) > 0)
        elif kind == "party_count":
            got = r["count"][0]
        elif kind == "tower_foes":
            # what = challenge type; want = number of opposing battlers. Each must be a
            # species from that challenge's first floor; every battler is Lv. 50.
            b = r["battle"] or bytes(4 * 0x58)
            allowed = tower_floor1_species(what)
            foes = [b[0x58 * i] | (b[0x58 * i + 1] << 8) for i in (1, 3)[:want]]
            levels = [b[0x58 * i + 0x2A] for i in ((0, 1) if want == 1 else (0, 1, 2, 3))]
            got = want if all(f in allowed for f in foes) and all(l == 50 for l in levels) else f"species {foes} levels {levels}"
        elif kind == "bag_has":
            item = const(what) if what in DEFS else ITEMS[what]
            got = int(any(r["bag"][i] | (r["bag"][i + 1] << 8) == item for i in range(0, len(r["bag"]), 4)))
        elif kind == "bag_any":
            ids = {ITEMS[w] for w in what}
            got = int(any(r["bag"][i] | (r["bag"][i + 1] << 8) in ids for i in range(0, len(r["bag"]), 4)))
            what = "/".join(w[5:] for w in what)
        elif kind == "foe":
            b = r["battle"] or bytes(4 * 0x58)
            got = (b[0x58] | (b[0x59] << 8), b[0x58 + 0x2A])
            want = (species_id(what), want)
        if got != want:
            fails.append(f"{kind} {what}: expected {want}, got {got}")
    return fails


def main():
    args = sys.argv[1:]
    outdir = os.path.join(R, "playtest_out")
    if "--out" in args:
        i = args.index("--out")
        outdir = os.path.abspath(args[i + 1])
        del args[i:i + 2]
    names = args or list(CHECKS)
    if not os.path.exists(HARNESS):
        sys.exit(f"Build the harness first:\n  gcc -O2 -w -o {HARNESS} {HARNESS}.c -lmgba")
    workdir = tempfile.mkdtemp(prefix="playtest_")
    failed = 0
    for name in names:
        try:
            fails = check(name, CHECKS[name], workdir, outdir)
        except Exception as e:  # build or harness trouble counts as a failure
            fails = [str(e)]
        print(f"{'PASS' if not fails else 'FAIL'}  {name}")
        for f in fails:
            print("      " + f)
        failed += bool(fails)
    subprocess.run(["make", "-j8"], cwd=R, capture_output=True)  # leave the normal ROM built
    print(f"\n{len(names) - failed}/{len(names)} checks passed. Screenshots: {outdir}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
