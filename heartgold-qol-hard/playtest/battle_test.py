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
--level-offset. Each has a sensible moveset from level-up moves and TMs
and a type-boosting item, but random IVs and natures and no EVs, and the
tester never switches or heals, so it is a yardstick, not a good player.

It reports, per trainer: won or lost, turns taken, how many of the player's
Pokemon fainted, and "stuck" with a screenshot when the battle did not end
(a crash, a softlock or a screen the tester does not understand), plus a
save state of that moment.
"""
import json
import os
import re
import subprocess
import sys

REFERENCE = ["CYNDAQUIL", "MAREEP", "GEODUDE", "MAGIKARP", "ABRA", "HERACROSS"]
INTRO = ([("wait", 900)] + [("key", "a")] * 80 + [("key", "start"), ("key", "a"), ("wait", 120)]
         + [("key", "a")] * 60 + [("wait", 300), ("hold", "up", 10), ("wait", 30)])
TAG_PARTNERS = {733, 734, 735, 736, 737}   # teams for the tag battle in Dragon's Den, not fought alone
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
    items = ids(read("include/constants/item.h"), "ITEM")
    sys.path.insert(0, os.path.join(tree, "tools", "hack"))
    cwd = os.getcwd()
    os.chdir(tree)                 # boss_teams.py reads the hack's data relative to the tree
    import boss_teams
    os.chdir(cwd)
    trainers = {}
    for m in re.finditer(r"^    \[(\d+)\] = \{\n        \.name = \"(.*?)\",(.*?)^    \},\n", read("data/Trainers.c"), re.S | re.M):
        levels = [int(x) for x in re.findall(r"\.level = (\d+),", m.group(3))]
        if levels:
            trainers[int(m.group(1))] = dict(
                name=m.group(2), levels=levels,
                cls=re.search(r"\.trainerClass = TRAINERCLASS_(\w+)", m.group(3)).group(1),
                single=re.search(r"\.battleType = (\w+)", m.group(3)).group(1) == "SINGLE_BATTLE")
    return dict(species=species, evolutions=evolutions, trainers=trainers, items=items, boss_teams=boss_teams)


def reference_party(data, level):
    """The reference party at this level: (name, species id, best move slot, move ids, item id) each.

    Moves and items come from the hack's own boss team tool: the best move of each of the Pokemon's types, a
    coverage move and a status or set-up move, from what it can learn by level-up or from a TM in the game,
    and the item that boosts its first type.
    """
    bt = data["boss_teams"]
    party = []
    for name in REFERENCE:
        while name in data["evolutions"] and data["evolutions"][name][0] <= level:
            name = data["evolutions"][name][1]
        moves = bt.pick_moves(name, level, False)
        best = max(range(len(moves)), key=lambda i: bt.move_score(name, moves[i])) if moves else 0
        item = bt.TYPE_ITEM.get(bt.SPECIES[name]["types"][0], "SITRUS_BERRY")
        party.append((name, data["species"][name], best, [bt.MOVE_IDS[m] for m in moves], data["items"][item]))
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
    blue = lambda c: 170 < c[2] < 225 and c[0] < 70 and 120 < c[1] < 165   # not the lighter blue of the shift screen
    if blue(px(30, 355)) and blue(px(225, 355)):
        return "moves"                     # the wide blue CANCEL button under the four moves
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
    for i, (_, species_id, _, moves, item) in enumerate(party):
        game.set_var(0x4000 + i, species_id)
        game.set_var(0x4006 + i, level)
        game.set_var(0x4010 + i, item)
        for j in range(4):
            game.set_var(0x4020 + 4 * i + j, moves[j] if j < len(moves) else 0)
    game.set_var(0x400C, trainer_id)
    game.set_var(0x400F, 0)
    game.key("a")
    order = list(range(6))   # which reference Pokemon is in each on-screen party slot
    turns, faints, last_menu, toggle, pending = 0, 0, 0, 0, 0
    skipped = {}             # per reference Pokemon: how many moves it has had refused
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
            best, known = party[order[0]][2], len(party[order[0]][3])
            slot = (best + skipped.get(order[0], 0)) % max(known, 1)
            game.touch(128, 73, after=40)
            game.touch(*MOVE_BUTTONS[slot], after=90)
        elif state == "moves":
            # still on the move list: the move was refused (no PP, disabled...), so use the next one from now on
            last_menu = game.frames
            best, known = party[order[0]][2], len(party[order[0]][3])
            skipped[order[0]] = skipped.get(order[0], 0) + 1
            game.touch(*MOVE_BUTTONS[(best + skipped[order[0]]) % max(known, 1)], after=90)
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
    state = os.path.join(out_dir, "stuck_%d.dst" % trainer_id)
    game.emu.savestate.save_file(state)   # load this in the emulator to look at the stuck battle
    return dict(result="stuck", turns=turns, faints=faints, frames=game.frames, screenshot=shot, savestate=state)


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
        ids = [i for i, t in trainers.items() if t["single"] and BOSS_CLASS.search(t["cls"])
               and i not in TAG_PARTNERS and t["name"] != "Mickey"]
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
