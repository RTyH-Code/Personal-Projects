#!/usr/bin/env python3
"""Story playthrough bot for HeartGold QoL + Hard.

    story_bot.py TEST_ROM TREE DUMP OUT [--from STAGE] [--until STAGE]

TEST_ROM is a build of the hack with the harness from make_harness.py, TREE
the hg-engine tree it was built from and DUMP a vanilla `make dump_scripts`
tree. It needs py-desmume and ndspy.

The bot plays the real story, with every step walked and every scene and
forced battle taken as a player would. The only help it gets is a team: at
the start, the harness gives five level-appropriate Pokemon from the bedroom
PC, so the bot does not have to catch and train. Its own starter from
Professor Elm joins them.

The story is a list of stages. After each one the bot saves a save state
(OUT/stage_NAME.dst), so a later run can start from any stage with --from.
When the bot is stuck (it cannot reach a place, a scene does not end, a
battle is lost) it stops and writes OUT/stuck.png, OUT/stuck.dst and a note.
Results go to OUT/story.json.
"""
import json
import os
import struct
import subprocess
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import battle_test
import walk_test
from walk_test import DIRS, text_box

TEAM_LEVEL = 16
FIELD_SYSTEM_AVATAR = 0x40          # FieldSystem.playerAvatar
FIELD_SYSTEM_LOCATION = 0x20        # FieldSystem.location -> {mapId, warpId, x, y, direction}
FIELD_SYSTEM_OBJECTS = 0x3C         # FieldSystem.mapObjectManager -> {flags, objectCount, ..., objects at 0x124}
OBJECT_SIZE = 0x12C                 # LocalMapObject: flags, flags2, id, ..., currentX at 0x64, currentZ at 0x6C
SURF = {0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x19, 0x2A, 0x50, 0x51, 0x52, 0x53, 0x73, 0x78, 0x7C}
LEDGES = {0x38: "right", 0x39: "left", 0x3A: "up", 0x3B: "down"}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}


class Stuck(Exception):
    pass


class Bot:
    def __init__(self, rom, tree, dump, out_dir):
        self.out = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self.world = walk_test.World(rom, tree, dump)
        self.data = battle_test.load(tree)
        self.game = walk_test.Walker(rom)
        self.names = {v: k for k, v in self.world.map_ids.items()}
        self.fs = None
        self.log = []

    # ------------------------------------------------------------ reading the game

    def field_system(self):
        """The FieldSystem: the structure whose playerAvatar is the avatar the game asks about."""
        g = self.game
        if not g.avatar:
            return None
        if self.fs and g.word(self.fs + FIELD_SYSTEM_AVATAR) == g.avatar:
            return self.fs
        ram = bytes(g.emu.memory.unsigned[0x02000000:0x02400000])
        needle = struct.pack("<I", g.avatar)
        at = ram.find(needle)
        while at >= 0:
            base = 0x02000000 + at - FIELD_SYSTEM_AVATAR
            loc = g.word(base + FIELD_SYSTEM_LOCATION)
            if 0x02000000 <= loc < 0x02400000 and g.word(loc) < 1000:
                self.fs = base
                return base
            at = ram.find(needle, at + 4)
        return None

    def where(self):
        """(map code, x, z), or None when there is no player on a map."""
        p = self.game.position()
        fs = self.field_system() if p else None
        if not p or not fs:
            return None
        map_id = self.game.word(self.game.word(fs + FIELD_SYSTEM_LOCATION))
        return self.names.get(map_id, str(map_id)), p[1], p[2]

    def objects(self):
        """The people and things on the map now: {object id: (x, z)}. The id is the object's place in the map's
        list of object events (the player is not in that list)."""
        g, fs = self.game, self.field_system()
        out = {}
        if not fs:
            return out
        manager = g.word(fs + FIELD_SYSTEM_OBJECTS)
        count, array = g.word(manager + 4), g.word(manager + 0x124)
        for i in range(min(count, 64)):
            obj = array + OBJECT_SIZE * i
            if g.word(obj) & 1 and obj != g.word(g.avatar + 0x30):
                out[g.word(obj + 8)] = (g.word(obj + 0x64), g.word(obj + 0x6C))
        return out

    def facing(self):
        p = self.game.position()
        return {0: "up", 1: "down", 2: "left", 3: "right"}.get(p[3]) if p else None

    # ------------------------------------------------------------- the map

    def tiles(self, code):
        """Walkable tiles of the matrix the map is in: {(x, z): behaviour}. Outdoors this is the whole region."""
        grid, _ = self.world.grid(self.world.headers[code]["matrix"])
        return {p: v & 0xFF for p, v in grid.items() if not v & 0x8000}

    def people(self, code):
        here = self.where()
        if here and here[0] == code:
            return set(self.objects().values())
        return {(e["x"], e["z"]) for e in self.world.events(code).get("object_events", [])}

    def path(self, code, start, goals, avoid=frozenset()):
        """Shortest list of directions from start to any goal tile, or None."""
        tiles = self.tiles(code)
        blocked = (self.people(code) | set(avoid)) - set(goals)
        seen = {start: None}
        queue = deque([start])
        while queue:
            here = queue.popleft()
            if here in goals:
                steps = []
                while seen[here]:
                    here, d = seen[here]
                    steps.append(d)
                return steps[::-1]
            for d, (dx, dz, _) in DIRS.items():
                nxt = (here[0] + dx, here[1] + dz)
                b = tiles.get(nxt)
                if b is None or b in SURF or nxt in blocked or nxt in seen:
                    continue
                if b in LEDGES:
                    if LEDGES[b] != d:
                        continue
                    nxt = (nxt[0] + dx, nxt[1] + dz)   # a ledge is jumped in one move
                    if nxt in seen or tiles.get(nxt) is None:
                        continue
                seen[nxt] = (here, d)
                queue.append(nxt)
        return None

    # ------------------------------------------------------------- moving

    def stuck(self, why):
        self.game.shot(os.path.join(self.out, "stuck.png"))
        self.save(os.path.join(self.out, "stuck.dst"))
        raise Stuck("%s (at %s)" % (why, self.where()))

    def free(self):
        """Whether the player can move: on a map, no message open, not in a battle or a menu."""
        return self.game.in_field() and not text_box(self.game.emu.screenshot())

    def settle(self, answers=(), limit=4000):
        """Press through messages, scenes and battles until the player is free again. `answers` are the buttons
        for the yes/no questions met on the way, in order (A for yes, B for no); after them, A."""
        answers = list(answers)
        frames = 0
        calm = 0
        while frames < limit:
            g = self.game
            if g.in_field():
                if text_box(g.emu.screenshot()):
                    calm = 0
                    g.key(answers.pop(0) if answers and self.question() else "a", after=20)
                    frames += 26
                    continue
                calm += 1
                if calm >= 8:             # a scene can pause between lines, so be sure it has ended
                    return
                g.run(20)
                frames += 20
                continue
            calm = 0
            if self.in_battle():
                self.battle()
                continue
            g.key("a", after=20)
            frames += 26
        self.stuck("a scene did not end")

    def question(self):
        """A yes/no question waiting for an answer: the two big buttons on the touch screen."""
        image = self.game.emu.screenshot()
        px = lambda x, y: image.getpixel((x, y))[:3]
        light = lambda c: min(c) > 150
        return light(px(200, 192 + 72)) and light(px(200, 192 + 120)) and not light(px(30, 192 + 96))

    def step(self, d):
        before = self.game.position()
        self.game.key(d, hold=14, after=4)
        for _ in range(6):
            p = self.game.position()
            if p and before and p[1:3] != before[1:3]:
                return True
            self.game.run(4)
        return False

    def walk(self, code, goals, avoid=(), face=None):
        """Walk to one of the goal tiles of the map, dealing with whatever happens on the way."""
        goals = {tuple(g) for g in goals}
        avoid = set(avoid)
        for attempt in range(60):
            self.settle()
            here = self.where()
            if not here:
                continue
            if here[0] != code and not self.same_region(here[0], code):
                self.stuck("on %s, not %s" % (here[0], code))
            pos = (here[1], here[2])
            if pos in goals:
                if face and self.facing() != face:
                    self.game.key(face, hold=2, after=10)
                return pos
            route = self.path(here[0], pos, goals, avoid)
            if route is None and avoid:
                avoid = set()                 # whoever was in the way may have moved on
                route = self.path(here[0], pos, goals, avoid)
            if route is None:
                self.stuck("no path on %s from %s to %s" % (here[0], pos, sorted(goals)[:4]))
            for d in route:
                if not self.step(d):
                    if not self.free():
                        break                     # something happened: deal with it and plan again
                    if self.step(d):
                        continue                  # only slowed down
                    if not self.free():
                        break
                    dx, dz, _ = DIRS[d]
                    cur = self.where()
                    if cur:
                        avoid.add((cur[1] + dx, cur[2] + dz))   # someone in the way
                    break
        self.stuck("could not reach %s on %s" % (sorted(goals)[:4], code))

    def same_region(self, a, b):
        return self.world.headers[a]["matrix"] == self.world.headers[b]["matrix"] == 0

    def go_through(self, code, warp_index, into=None):
        """Use a warp of the map: walk onto it (a door or stairs) and, for warps at the edge of a room, keep
        walking `into` it. Waits until the next map has loaded."""
        warp = self.world.events(code)["warp_events"][warp_index]
        tile = (warp["x"], warp["z"])
        grid, _ = self.world.grid(self.world.headers[code]["matrix"])
        if into is None:
            behaviour = grid.get(tile, 0) & 0xFF     # a door is a blocked tile with the door behaviour
            into = {0x6C: "right", 0x6D: "left", 0x6E: "up", 0x6F: "down", 0x62: "right", 0x63: "left",
                    0x64: "up", 0x65: "down", 0x69: "up", 0x5E: "right", 0x5F: "left"}.get(behaviour)
        if into:
            dx, dz, _ = DIRS[into]
            self.walk(code, [(tile[0] - dx, tile[1] - dz)])
            for _ in range(3):
                self.game.key(into, hold=16, after=4)
                if self.arrived(code):
                    return
        else:
            self.walk(code, [tile])
            if self.arrived(code):
                return
        self.stuck("warp %d of %s did not work" % (warp_index, code))

    def arrived(self, old):
        for _ in range(40):
            self.game.run(10)
            here = self.where()
            if here and here[0] != old and self.free():
                return True
        return False

    def talk(self, code, target, answers=()):
        """Stand next to a person or thing and press A facing it; then see the scene through. `target` is a tile
        (x, z), or the number of a person in the map's list of object events, wherever they now stand."""
        if isinstance(target, int):
            self.settle()
            people = self.objects()
            if target not in people:
                self.stuck("person %d is not on %s" % (target, code))
            target = people[target]
        options = {}
        for d, (dx, dz, _) in DIRS.items():
            options[(target[0] - dx, target[1] - dz)] = d
        tiles = self.tiles(code)
        options = {t: d for t, d in options.items() if t in tiles}
        pos = self.walk(code, options, avoid={target})
        self.game.key(options[pos], hold=2, after=10)
        self.game.key("a", after=30)
        self.settle(answers)

    # ------------------------------------------------------------- battles

    def in_battle(self):
        return battle_test.screen_state(self.game.emu.screenshot()) != "other" or self.battle_screen()

    def battle_screen(self):
        image = self.game.emu.screenshot()
        r, g, b = image.getpixel((128, 192 + 55))[:3]
        return r > 190 and g < 110 and b < 120

    def battle(self):
        """Fight until the battle ends: the strongest move each turn, the next Pokemon when one faints."""
        g = self.game
        order = list(range(6))
        pending, toggle, frames = 0, 0, 0
        while not g.in_field() and frames < 60 * 60 * 20:
            image = g.emu.screenshot()
            state = battle_test.screen_state(image)
            if state == "menu":
                g.touch(128, 73, after=40)
                g.touch(*battle_test.MOVE_BUTTONS[0], after=90)
                frames += 130
            elif state == "moves":
                toggle += 1
                g.touch(*battle_test.MOVE_BUTTONS[toggle % 4], after=90)
                frames += 90
            elif state == "party":
                slots = [battle_test.party_slot(image, i) for i in range(6)]
                choice = next((i for i in range(1, 6) if slots[i] == "alive"), None)
                if choice is None:
                    g.key("b")
                else:
                    pending = choice
                    g.touch(*battle_test.PARTY_SLOTS[choice], after=40)
                frames += 40
            elif state == "confirm":
                g.touch(128, 70, after=90)
                frames += 90
            else:
                toggle += 1
                g.key("a" if toggle % 3 else "b", after=30)
                frames += 36
        if not g.in_field():
            self.stuck("a battle did not end")
        self.log.append(("battle", self.where()))

    # ------------------------------------------------------------- the run

    def save(self, path):
        # a state saved straight after skipped frames can crash the emulator when it is loaded again
        self.game.run_every_frame(30)
        self.game.emu.savestate.save_file(path)

    def start(self, state):
        """From the bedroom save state: the harness gives the team at the PC."""
        g = self.game
        g.emu.savestate.load_file(state)
        g.vars_pointer = None
        g.run(40)
        team = battle_test.reference_party(self.data, TEAM_LEVEL)[:5]
        for i in range(6):
            mon = team[i] if i < len(team) else None
            g.set_var(0x4000 + i, mon[1] if mon else 0)
            g.set_var(0x4006 + i, TEAM_LEVEL)
            g.set_var(0x4010 + i, mon[4] if mon else 0)
            for j in range(4):
                g.set_var(0x4020 + 4 * i + j, mon[3][j] if mon and j < len(mon[3]) else 0)
        g.set_var(0x400E, 3)
        g.key("a")
        self.settle()


def main():
    args = sys.argv[1:]

    def option(name, default):
        if name in args:
            i = args.index(name)
            value = args[i + 1]
            del args[i:i + 2]
            return value
        return default
    first = option("--from", None)
    last = option("--until", None)
    rom, tree, dump, out = args[:4]
    os.makedirs(out, exist_ok=True)
    state = os.path.join(out, "bedroom.dst")
    if not os.path.exists(state):
        subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "walk_test.py"),
                        rom, tree, dump, out, "--make-state"], check=True)
    import story
    bot = Bot(rom, tree, dump, out)
    stages = story.STAGES
    names = [s.__name__ for s in stages]
    begin = names.index(first) if first else 0
    end = names.index(last) + 1 if last else len(stages)
    if begin == 0:
        bot.start(state)
    else:
        bot.game.run(400)        # the emulator can crash when a state is loaded before it has run a little
        bot.game.emu.savestate.load_file(os.path.join(out, "stage_%s.dst" % names[begin - 1]))
        bot.game.run(60)
    results = []
    for stage in stages[begin:end]:
        frames = bot.game.frames
        try:
            stage(bot)
        except Stuck as e:
            results.append(dict(stage=stage.__name__, result="stuck", note=str(e)))
            print("%-24s STUCK  %s" % (stage.__name__, e), flush=True)
            break
        bot.save(os.path.join(out, "stage_%s.dst" % stage.__name__))
        results.append(dict(stage=stage.__name__, result="ok", at=bot.where(), frames=bot.game.frames - frames))
        print("%-24s ok     at %s" % (stage.__name__, bot.where()), flush=True)
    json.dump(results, open(os.path.join(out, "story.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
