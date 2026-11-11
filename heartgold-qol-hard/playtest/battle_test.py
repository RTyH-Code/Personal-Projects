#!/usr/bin/env python3
"""Battle harness playtester: fight trainers automatically in the emulator.

Needs a test ROM built with make_harness.py and py-desmume. For each trainer
it loads a save state taken in the player's bedroom, writes a reference
party and the trainer's number into the harness variables, starts the battle
at the bedroom PC and plays it by reading the screen: it always uses each
Pokemon's strongest move and sends in the next Pokemon when one faints.

    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \\
        python3 playtest/battle_test.py TEST_ROM HG_ENGINE_TREE OUT_DIR [--bosses | --all | ids...]
            [--level-offset N] [--jobs N]

The reference party is six common picks (the Cyndaquil, Mareep, Geodude,
Magikarp and Abra lines and Heracross), evolved as far as their level
allows, all at the level of the trainer's strongest Pokemon plus
--level-offset. It has no held items and only level-up moves, so it is a
plain yardstick, not a good player.

It reports, per trainer: won or lost, turns taken, how many of the player's
Pokemon fainted, and "stuck" with a screenshot when the battle did not end
(a crash, a softlock or a screen the tester does not understand).
"""
import json
import os
import re
import subprocess
import sys

REFERENCE = ["CYNDAQUIL", "MAREEP", "GEODUDE", "MAGIKARP", "ABRA", "HERACROSS"]
INTRO = ([("wait", 900)] + [("key", "a")] * 80 + [("key", "start"), ("key", "a"), ("wait", 120)]
         + [("key", "a")] * 60 + [("wait", 300), ("hold", "up", 10), ("wait", 30)])
BOSS_CLASS = re.compile(r"LEADER_|ELITE_FOUR_|CHAMPION|RIVAL|PKMN_TRAINER_RED|EXECUTIVE|KIMONO_GIRL")
MOVE_BUTTONS = [(64, 50), (190, 50), (64, 105), (190, 105)]
PARTY_SLOTS = [(64, 25), (190, 33), (64, 72), (190, 80), (64, 120), (190, 128)]
MAX_FRAMES = 60 * 60 * 25      # 25 minutes of game time per battle
STUCK_FRAMES = 60 * 60 * 3     # no menu seen for three minutes


# ------------------------------------------------------------------ data

def load(tree):
    read = lambda p: open(os.path.join(tree, p)).read()
    ids = lambda text, prefix: {n: int(v) for n, v in re.findall(r"#define %s_(\w+)\s+\(?(\d+)\)?\s*$" % prefix, text, re.M)}
    species = ids(read("include/constants/species.h"), "SPECIES")
    moves = {}
    for m in re.finditer(r"^    \[MOVE_(\w+)\] = \{\n(.*?)^    \},\n", read("data/Moves.c"), re.S | re.M):
        get = lambda k: re.search(r"\.%s = ([^,]+)," % k, m.group(2)).group(1)
        num = lambda v: int(re.findall(r"\d+", v)[0])
        moves[m.group(1)] = dict(power=num(get("power")), type=re.findall(r"TYPE_(\w+)", get("type"))[0], split=get("split"))
    stats = {}
    for m in re.finditer(r"^    \[SPECIES_(\w+)\] = \{\n(.*?)^    \},\n", read("data/Species.c"), re.S | re.M):
        b = re.search(r"\.baseStats = \{(.*?)\}", m.group(2), re.S)
        if b:
            s = {k: int(v) for k, v in re.findall(r"\.(\w+) = (\d+)", b.group(1))}
            stats[m.group(1)] = (s, re.findall(r"TYPE_(\w+)", re.search(r"\.types = \{(.*?)\}", m.group(2)).group(1)))
    evolutions = {}
    for m in re.finditer(r"^    \[SPECIES_(\w+)\] = \{(.*?)^    \},", read("data/Evolutions.c"), re.S | re.M):
        for method, param, target in re.findall(r"\{ (EVO_\w+), (\d+), SPECIES_(\w+) \}", m.group(2)):
            if method == "EVO_LEVEL":
                evolutions.setdefault(m.group(1), (int(param), target))
    learnsets = json.loads(read("data/learnsets/learnsets.json"))
    trainers = {}
    for m in re.finditer(r"^    \[(\d+)\] = \{\n        \.name = \"(.*?)\",(.*?)^    \},\n", read("data/Trainers.c"), re.S | re.M):
        levels = [int(x) for x in re.findall(r"\.level = (\d+),", m.group(3))]
        if levels:
            trainers[int(m.group(1))] = dict(
                name=m.group(2), levels=levels,
                cls=re.search(r"\.trainerClass = TRAINERCLASS_(\w+)", m.group(3)).group(1),
                single=re.search(r"\.battleType = (\w+)", m.group(3)).group(1) == "SINGLE_BATTLE")
    return dict(species=species, moves=moves, stats=stats, evolutions=evolutions, learnsets=learnsets, trainers=trainers)


def reference_party(data, level):
    """(species name, id, index of its best move) for the reference party at this level."""
    party = []
    for name in REFERENCE:
        while name in data["evolutions"] and data["evolutions"][name][0] <= level:
            name = data["evolutions"][name][1]
        known = []
        for entry in data["learnsets"]["SPECIES_" + name]["LevelMoves"]:
            move = entry["Move"][5:]
            if entry["Level"] <= level and move not in known:
                known.append(move)
        known = known[-4:]   # a new Pokemon knows its four most recent level-up moves
        stat, types = data["stats"][name]

        def score(move):
            m = data["moves"].get(move)
            if not m or m["power"] <= 1 or "STATUS" in m["split"]:
                return 0
            attack = stat["attack"] if "PHYSICAL" in m["split"] else stat["spAttack"]
            return m["power"] * attack * (1.5 if m["type"] in types else 1)
        best = max(range(len(known)), key=lambda i: score(known[i])) if known else 0
        party.append((name, data["species"][name], best, len(known)))
    return party


# -------------------------------------------------------------- emulator

class Game:
    def __init__(self, rom):
        from desmume.controls import Keys, keymask
        from desmume.emulator import DeSmuME
        self.emu = DeSmuME()
        self.emu.open(rom)
        self.emu.volume_set(0)
        self.keys = {"a": keymask(Keys.KEY_A), "b": keymask(Keys.KEY_B), "start": keymask(Keys.KEY_START),
                     "up": keymask(Keys.KEY_UP)}
        self.vars_pointer = None
        # Save_VarsFlags_CheckFlagInArray(state, flag): r0 is the script variable block
        self.emu.memory.register_exec(0x020503DC, self._grab)
        self.frames = 0

    def _grab(self, address, size):
        if self.vars_pointer is None:
            self.vars_pointer = self.emu.memory.register_arm9.r0 & 0xFFFFFFFF

    def run(self, frames):
        for i in range(frames):
            if i < frames - 1:
                self.emu.skip_next_frame()   # only the last frame is drawn; the rest run faster
            self.emu.cycle(with_joystick=False)
        self.frames += frames

    def key(self, name, hold=6, after=24):
        self.emu.input.keypad_add_key(self.keys[name])
        self.run(hold)
        self.emu.input.keypad_rm_key(self.keys[name])
        self.run(after)

    def touch(self, x, y, after=24):
        self.emu.input.touch_set_pos(x, y)
        self.run(6)
        self.emu.input.touch_release()
        self.run(after)

    def set_var(self, var, value):
        a = self.vars_pointer + 2 * (var - 0x4000)
        self.emu.memory.unsigned[a] = value & 0xFF
        self.emu.memory.unsigned[a + 1] = value >> 8

    def get_var(self, var):
        a = self.vars_pointer + 2 * (var - 0x4000)
        return self.emu.memory.unsigned[a] | (self.emu.memory.unsigned[a + 1] << 8)

    def make_state(self, path):
        for step in INTRO:
            if step[0] == "wait":
                self.run(step[1])
            elif step[0] == "key":
                self.key(step[1])
            else:
                self.key(step[1], hold=step[2], after=0)
        self.emu.savestate.save_file(path)


def screen_state(image):
    """Which battle screen is showing, from a few pixels of the screenshot (bottom screen starts at y=192)."""
    px = lambda x, y: image.getpixel((x, y))[:3]
    r, g, b = px(128, 192 + 55)
    if r > 190 and g < 110 and b < 120:
        return "menu"                      # the red FIGHT button
    tr, tg, tb = px(128, 168)
    if abs(tr - tg) < 12 and abs(tg - tb) < 12 and 90 < tr < 170:   # top-screen text box greyed out
        sr, sg, sb = px(60, 192 + 172)
        if sb > 150 and sr < 120:
            return "confirm"               # the SUMMARY button of the shift screen
        return "party"
    return "other"


def party_slot(image, slot):
    """"alive" (green panel), "fainted" (orange) or "empty" (grey), by majority of three points on the panel."""
    x, y = PARTY_SLOTS[slot]
    votes = []
    for dx, dy in ((40, -14), (50, 2), (-10, 16)):
        r, g, b = image.getpixel((x + dx, 192 + y + dy))[:3]
        votes.append("alive" if g > r + 30 else "fainted" if r > g + 40 else "empty")
    return max(set(votes), key=votes.count)


def fight(game, state_path, data, trainer_id, level, out_dir):
    game.emu.savestate.load_file(state_path)
    game.vars_pointer = None
    game.frames = 0
    game.run(40)
    if game.vars_pointer is None:
        return dict(result="stuck", note="could not find the script variables")
    party = reference_party(data, level)
    for i, (_, species_id, _, _) in enumerate(party):
        game.set_var(0x4000 + i, species_id)
        game.set_var(0x4006 + i, level)
        game.set_var(0x4010 + i, 0)
    game.set_var(0x400C, trainer_id)
    game.set_var(0x400F, 0)
    game.key("a")
    order = list(range(6))   # which reference Pokemon is in each on-screen party slot
    turns, faints, last_menu, toggle, pending = 0, 0, 0, 0, 0
    while game.frames < MAX_FRAMES:
        result = game.get_var(0x400F)
        if result:
            won = result == 2
            return dict(result="won" if won else "lost", turns=turns, faints=faints if won else len(party),
                        frames=game.frames)
        image = game.emu.screenshot()
        state = screen_state(image)
        if state == "menu":
            last_menu = game.frames
            turns += 1
            _, _, best, known = party[order[0]]
            slot = best if turns % 12 else (turns // 12) % max(known, 1)   # now and then try another move (PP)
            game.touch(128, 73, after=40)
            game.touch(*MOVE_BUTTONS[slot], after=90)
        elif state == "party":
            last_menu = game.frames
            slots = [party_slot(image, i) for i in range(6)]
            faints = max(faints, slots.count("fainted"))
            choice = next((i for i in range(1, 6) if slots[i] == "alive"), None)
            if choice is None:
                game.key("b")
            else:
                pending = choice
                game.touch(*PARTY_SLOTS[choice], after=40)
        elif state == "confirm":
            last_menu = game.frames
            game.touch(128, 70, after=90)
            if pending:   # the Pokemon sent in swaps places with the one in front
                order[0], order[pending] = order[pending], order[0]
                pending = 0
        else:
            toggle += 1
            game.key("a" if toggle % 3 else "b", after=30)
        if game.frames - last_menu > STUCK_FRAMES and game.frames > STUCK_FRAMES:
            break
    shot = os.path.join(out_dir, "stuck_%d.png" % trainer_id)
    game.emu.screenshot().save(shot)
    return dict(result="stuck", turns=turns, faints=faints, frames=game.frames, screenshot=shot)


# ------------------------------------------------------------------ main

def worker(rom, tree, out_dir, state_path, level_offset, ids, out_file):
    data = load(tree)
    game = Game(rom)
    results = {}
    for trainer_id in ids:
        t = data["trainers"][trainer_id]
        level = max(1, min(100, max(t["levels"]) + level_offset))
        r = fight(game, state_path, data, trainer_id, level, out_dir)
        r.update(name=t["name"], cls=t["cls"], ace=max(t["levels"]), size=len(t["levels"]), party_level=level)
        results[trainer_id] = r
        print("%4d %-10s %-22s ace %-3d x%d  party Lv. %-3d %-5s turns %-3s faints %s" % (
            trainer_id, t["name"], t["cls"][:22], r["ace"], r["size"], level, r["result"], r.get("turns", "-"),
            r.get("faints", "-")), flush=True)
        json.dump(results, open(out_file, "w"), indent=1)


def main():
    args = sys.argv[1:]
    def option(name, default):
        if name in args:
            i = args.index(name)
            value = args[i + 1]
            del args[i:i + 2]
            return value
        return default
    level_offset = int(option("--level-offset", "0"))
    jobs = int(option("--jobs", "1"))
    part = option("--part", None)
    rom, tree, out_dir = args[:3]
    selectors = args[3:]
    os.makedirs(out_dir, exist_ok=True)
    data = load(tree)
    trainers = data["trainers"]
    if "--all" in selectors:
        ids = [i for i, t in trainers.items() if t["single"] and t["name"] != "Mickey"]
    elif "--bosses" in selectors or not selectors:
        ids = [i for i, t in trainers.items() if t["single"] and BOSS_CLASS.search(t["cls"])]
    else:
        ids = [int(x) for x in selectors]
    ids.sort(key=lambda i: (max(trainers[i]["levels"]), i))
    state_path = os.path.join(out_dir, "bedroom.dst")
    if not os.path.exists(state_path):
        Game(rom).make_state(state_path)
    if part is not None:   # a worker started by --jobs
        k, n = map(int, part.split("/"))
        worker(rom, tree, out_dir, state_path, level_offset, ids[k::n], os.path.join(out_dir, "results_%d.json" % k))
        return
    procs = [subprocess.Popen([sys.executable, __file__, rom, tree, out_dir, "--level-offset", str(level_offset),
                               "--part", "%d/%d" % (k, jobs)] + selectors) for k in range(jobs)]
    for p in procs:
        p.wait()
    merged = {}
    for k in range(jobs):
        path = os.path.join(out_dir, "results_%d.json" % k)
        if os.path.exists(path):
            merged.update(json.load(open(path)))
    json.dump(merged, open(os.path.join(out_dir, "results.json"), "w"), indent=1)
    count = lambda r: sum(1 for x in merged.values() if x["result"] == r)
    print("%d battles: %d won, %d lost, %d stuck" % (len(merged), count("won"), count("lost"), count("stuck")))


if __name__ == "__main__":
    main()
