#!/usr/bin/env python3
"""Story playthrough bot for HeartGold QoL + Hard.

    story_bot.py TEST_ROM TREE DUMP OUT [--from STAGE] [--until STAGE]

TEST_ROM is a build of the hack with the harness from make_harness.py, TREE
the hg-engine tree it was built from and DUMP a vanilla `make dump_scripts`
tree. It needs py-desmume and ndspy.

The bot plays the real story, with every step walked and every scene and
forced battle taken as a player would. The only help it gets is a team: at
the start, the harness gives four level-appropriate Pokemon from the bedroom
PC, so the bot does not have to catch and train. Its own starter from
Professor Elm joins them.

The emulator now and then crashes on its own; the run then carries on from the
last stage that finished.

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
TEAM = (0, 1, 2, 4)          # of battle_test.REFERENCE: Cyndaquil, Mareep, Geodude and Abra, evolved to the level
FIELD_SYSTEM_AVATAR = 0x40          # FieldSystem.playerAvatar
FIELD_SYSTEM_LOCATION = 0x20        # FieldSystem.location -> {mapId, warpId, x, y, direction}
FIELD_SYSTEM_OBJECTS = 0x3C         # FieldSystem.mapObjectManager -> {flags, objectCount, ..., objects at 0x124}
FOLLOWER = 253                      # object id of the Pokemon that walks behind the player
OBJECT_SIZE = 0x12C                 # LocalMapObject: flags, flags2, id, ..., currentX at 0x64, currentZ at 0x6C
SURF = {0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x19, 0x2A, 0x50, 0x51, 0x52, 0x53, 0x73, 0x78, 0x7C}
LEDGES = {0x38: "right", 0x39: "left", 0x3A: "up", 0x3B: "down"}
LADDERS = {0x3C: "up", 0x3D: "down", 0x3E: "down"}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}

# The trainer AI. Each battler gets six controller handlers when a battle opens (overlay 12, 0x02260EA4, called
# with the BattleSystem and the battler's OpponentData): the player's read the touch screen, every other
# battler's run the trainer AI with its trainer's AI flags. The bot hands the player's side the same AI handlers
# and the flags every trainer in the hack has, so the game itself chooses the player's moves and switches.
BATTLER_SETUP = 0x02260EA4
AI_SELECT_MOVE = 0x0221BEF4     # overlay 10: the trainer AI choosing a move for battler r1; counted for the report
BATTLER_ID, BATTLER_IS_AI = 0x194, 0x196          # in OpponentData, after the six handlers at 0
BATTLE_TRAINERS, TRAINER_SIZE, TRAINER_AI_FLAGS = 0xAC, 0x34, 0x0C      # BattleSystem.trainers[4]
# The AI cannot answer "Will you switch your Pokemon?", so the bot plays with the Set battle style, as a player can
# choose in Options: whenever the game reads the style (Options_GetBattleStyle), the bit is set first.
OPTIONS_GET_BATTLE_STYLE, BATTLE_STYLE_SET = 0x0202AD90, 0x40
EXPERT_AI = 0x7                 # F_PRIORITIZE_SUPER_EFFECTIVE | F_EVALUATE_ATTACKS | F_EXPERT_ATTACKS


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
        self.battlers = {}          # battler id -> (BattleSystem, OpponentData) for the battle being opened
        self.game.emu.memory.register_exec(BATTLER_SETUP, self._battler_setup)
        self.game.emu.memory.register_exec(OPTIONS_GET_BATTLE_STYLE, self._set_style)
        self.ai_moves = 0           # moves the AI chose for the player's side
        self.game.emu.memory.register_exec(AI_SELECT_MOVE, self._ai_move)

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

    def flag(self, name):
        g = self.game
        f = self.world.flags[name]
        return bool(g.emu.memory.unsigned[g.vars_pointer + walk_test.FLAGS_OFFSET + f // 8] >> (f % 8) & 1)

    def expect(self, name, what):
        """Stop if a story flag that the stage should have set is not set."""
        if not self.flag(name):
            self.stuck("%s did not happen (%s is not set)" % (what, name))

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
            # the walking Pokemon behind the player is no obstacle: the player swaps places with it
            return {p for i, p in self.objects().items() if i != FOLLOWER}
        return {(e["x"], e["z"]) for e in self.world.events(code).get("object_events", [])}

    def path(self, code, start, goals, avoid=frozenset()):
        """Shortest list of directions from start to any goal tile, or None."""
        tiles = self.tiles(code)
        warps = {(w["x"], w["z"]) for m in self.region_maps(code) for w in self.world.events(m).get("warp_events", [])}
        # don't walk into a warp on the way; a goal tile someone stands on (or was in the way at) can't be reached
        blocked = self.people(code) | set(avoid) | (warps - set(goals))
        on_ladder = LADDERS.get(tiles.get(start))
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
                if here == start and d == on_ladder:
                    continue                       # that would climb the ladder just arrived by
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
        presses = 0
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
            if self.in_pokegear():
                # a phone call: B to the end of it, then the bar at the foot of the Pokegear closes it
                g.key("b", after=30)
                g.key("b", after=30)
                g.touch(128, 175, after=60)
                frames += 140
                continue
            presses += 1
            # A for messages; on a naming screen A types letters and START jumps to OK
            g.key("start" if presses % 12 == 0 else "a", after=20)
            frames += 26
        self.stuck("a scene did not end")

    def in_pokegear(self):
        image = self.game.emu.screenshot()
        return image.getpixel((128, 8))[:3] == (40, 64, 240) and max(image.getpixel((20, 60))[:3]) < 110

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

    def walk(self, code, goals, avoid=(), face=None, leave_ok=False):
        """Walk to one of the goal tiles of the map, dealing with whatever happens on the way. With leave_ok,
        reaching another map instead (a warp on the goal tile) also ends the walk, returning None."""
        goals = {tuple(g) for g in goals}
        avoid = set(avoid)
        for attempt in range(60):
            self.settle()
            here = self.where()
            if not here:
                continue
            if here[0] != code and not self.same_region(here[0], code):
                if leave_ok:
                    return None
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
        entry, found = self.warp_entry(code, warp_index)   # a door is a blocked tile with the door behaviour
        if into is None:
            into = found
        if into and entry == tile:                          # a ladder
            if self.walk(code, [tile], leave_ok=True) is None or self.arrived(code, frames=60):
                return                                      # a ladder down is taken by stepping onto it
            for _ in range(3):
                self.game.key(into, hold=16, after=4)
                if self.arrived(code):
                    return
            self.stuck("ladder %d of %s did not work" % (warp_index, code))
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

    def warp_entry(self, code, index):
        """(tile to stand on, direction to walk into it or None) for a warp of the map."""
        warp = self.world.events(code)["warp_events"][index]
        tile = (warp["x"], warp["z"])
        grid, _ = self.world.grid(self.world.headers[code]["matrix"])
        into = {0x6C: "right", 0x6D: "left", 0x6E: "up", 0x6F: "down", 0x62: "right", 0x63: "left",
                0x64: "up", 0x65: "down", 0x69: "up", 0x5E: "right", 0x5F: "left"}.get(grid.get(tile, 0) & 0xFF)
        if into:
            dx, dz, _ = DIRS[into]
            return (tile[0] - dx, tile[1] - dz), into
        ladder = LADDERS.get(grid.get(tile, 0) & 0xFF)
        if ladder:
            return tile, ladder                  # stand on the ladder and climb it
        return tile, None

    def reach(self, code, start):
        """Every tile of the map (or outdoor region) the player can walk to from start, with its distance."""
        tiles = self.tiles(code)
        seen = {start: 0}
        queue = deque([start])
        while queue:
            here = queue.popleft()
            for d, (dx, dz, _) in DIRS.items():
                nxt = (here[0] + dx, here[1] + dz)
                b = tiles.get(nxt)
                if b is None or b in SURF:
                    continue
                if b in LEDGES:
                    if LEDGES[b] != d:
                        continue
                    nxt = (nxt[0] + dx, nxt[1] + dz)
                    if tiles.get(nxt) is None:
                        continue
                if nxt not in seen:
                    seen[nxt] = seen[here] + 1
                    queue.append(nxt)
        return seen

    def region_maps(self, code):
        if self.world.headers[code]["matrix"] != 0:
            return [code]
        return [m for m in self.world.map_ids if m in self.world.headers and self.world.headers[m]["matrix"] == 0
                and self.world.events(m).get("warp_events")]

    def route(self, target):
        """The warps to take, [(map, warp index)], to get from here to the target map, fewest steps first."""
        import heapq
        here = self.where()
        start = (here[0], (here[1], here[2]))
        best, queue, done = {start: (0, [])}, [(0, 0, start)], set()
        areas = []
        counter = 0
        while queue:
            cost, _, node = heapq.heappop(queue)
            if node in done:
                continue
            done.add(node)
            code, pos = node
            if code == target:
                return best[node][1]
            if len(done) > 2000:
                break
            # one flood fill for each walkable stretch: outdoors, many doors lead back to the same one
            key = self.world.headers[code]["matrix"] or code if code in self.world.headers else code
            dist = next((d for k, d in areas if k == key and pos in d), None)
            if dist is None:
                dist = self.reach(code, pos)
                areas.append((key, dist))
            if self.region_tiles(code, target, dist):
                return best[node][1]
            for m in self.region_maps(code):
                for i, warp in enumerate(self.world.events(m).get("warp_events", [])):
                    entry, _ = self.warp_entry(m, i)
                    if entry not in dist and (warp["x"], warp["z"]) != pos:
                        continue
                    dest = str(warp["dest_header_id"]).replace("MAP_", "")
                    if dest not in self.world.headers:
                        continue
                    arrivals = self.world.events(dest).get("warp_events", [])
                    if warp["dest_warp_id"] >= len(arrivals):
                        continue
                    a = arrivals[warp["dest_warp_id"]]
                    nxt = (dest, (a["x"], a["z"]))
                    c = cost + dist.get(entry, 0) + 10
                    if nxt not in best or c < best[nxt][0]:
                        best[nxt] = (c, best[node][1] + [(m, i)])
                        counter += 1
                        heapq.heappush(queue, (c, counter, nxt))
        self.stuck("no way found to %s" % target)

    def region_tiles(self, code, target, dist):
        """Of the tiles in dist, those of the target map, when code and target share the outdoor map."""
        if code not in self.world.headers or target not in self.world.headers or not self.same_region(code, target):
            return []
        owner = self.world.grid(0)[1]
        want = self.world.map_ids[target]
        return [p for p in dist if owner.get(p) == want]

    def travel(self, target):
        """Go to the target map by whatever warps lead there; outdoors, on until the player stands in it."""
        for _ in range(3):
            steps = self.route(target)
            for code, index in steps:
                self.go_through(code, index)
            here = self.where()
            if here and here[0] != target:
                dist = self.reach(here[0], (here[1], here[2]))
                goals = self.region_tiles(here[0], target, dist)
                if goals:
                    self.walk(target, [min(goals, key=dist.get)])
                    here = self.where()
            if here and here[0] == target:
                return
        self.stuck("did not get to %s" % target)

    def arrived(self, old, frames=400):
        for _ in range(frames // 10):
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

    def _battler_setup(self, address, size):
        r = self.game.emu.memory.register_arm9
        self.battlers[self.game.emu.memory.unsigned[(r.r1 & 0xFFFFFFFF) + BATTLER_ID]] = (r.r0 & 0xFFFFFFFF,
                                                                                         r.r1 & 0xFFFFFFFF)

    def _ai_move(self, address, size):
        if self.game.emu.memory.register_arm9.r1 & 0xFF in (0, 2):
            self.ai_moves += 1

    def _set_style(self, address, size):
        options = self.game.emu.memory.register_arm9.r0 & 0xFFFFFFFF
        self.game.emu.memory.unsigned[options] |= BATTLE_STYLE_SET

    def hand_to_ai(self):
        """Give the player's battlers the trainer AI: an opposing battler's handlers, and the expert AI flags."""
        g, mem = self.game, self.game.emu.memory.unsigned
        if 0 not in self.battlers or 1 not in self.battlers:
            return False
        for mine, theirs in ((0, 1), (2, 3)):
            if mine in self.battlers and theirs in self.battlers:
                bsys, od = self.battlers[mine]
                # the first five: commands, moves, targets, items, replacements. The sixth, the player's yes/no
                # (forget a move to learn a new one?), stays the player's: the AI's never answers it
                for i in range(5):
                    value = g.word(self.battlers[theirs][1] + 4 * i)
                    for j in range(4):
                        mem[od + 4 * i + j] = (value >> (8 * j)) & 0xFF
                mem[od + BATTLER_IS_AI] = 1
                at = bsys + BATTLE_TRAINERS + TRAINER_SIZE * mine + TRAINER_AI_FLAGS
                for j in range(4):
                    mem[at + j] = (EXPERT_AI >> (8 * j)) & 0xFF
        self.battlers = {}
        return True

    def battle(self):
        """Fight until the battle ends. The game's own trainer AI picks the player's moves and replacements
        (see hand_to_ai); the bot only moves the text on. Should a menu still show, it falls back to the first
        move and the next healthy Pokemon."""
        g = self.game
        ai = False
        for i in range(600):
            if self.hand_to_ai():
                ai = True
                break
            g.run(1)
        toggle, frames, menus = 0, 0, 0
        white = 0
        while not g.in_field() and frames < 60 * 60 * 20:
            image = g.emu.screenshot()
            # a battle lost fades both screens to white before the player wakes at a Pokemon Center
            if all(min(image.getpixel(p)[:3]) > 235 for p in ((20, 20), (128, 96), (236, 170), (128, 300))):
                white += 1
                if white > 30:
                    self.stuck("lost a battle: the team whited out")
            else:
                white = 0
            state = battle_test.screen_state(image)
            if state in ("menu", "moves", "party"):
                menus += 1
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
        self.log.append(dict(at=self.where(), ai=ai, menus=menus))

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
        # four of the reference families (not Magikarp, which only splashes at this level): with the starter
        # and the Mystery Egg from Elm's aide in Violet City, that fills the party
        party = battle_test.reference_party(self.data, TEAM_LEVEL)
        team = [party[i] for i in TEAM]
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
    """Run the stages in a child process. The emulator now and then crashes (most often right after loading a
    save state); then the run carries on from the last stage that finished, up to three times."""
    if "--child" in sys.argv:
        sys.argv.remove("--child")
        return run()
    args = sys.argv[1:]
    positional = [a for i, a in enumerate(args)
                  if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--from", "--until"))]
    out = positional[3]
    names = [s.__name__ for s in __import__("story").STAGES]
    done = []
    for attempt in range(4):
        child = subprocess.run([sys.executable, "-X", "faulthandler", __file__] + args + ["--child"])
        results = json.load(open(os.path.join(out, "story.json"))) if os.path.exists(os.path.join(out, "story.json")) else []
        done += results
        last = results[-1] if results else None
        if child.returncode >= 0 or (last and last["result"] != "ok"):
            break
        # crashed: start again after the last stage that finished
        finished = [r["stage"] for r in done if r["result"] == "ok"]
        if not finished:
            continue
        nxt = names.index(finished[-1]) + 1
        if nxt >= len(names):
            break
        if "--from" in args:
            args[args.index("--from") + 1] = names[nxt]
        else:
            args += ["--from", names[nxt]]
        print("the emulator crashed; carrying on from %s" % names[nxt], flush=True)
    json.dump(done, open(os.path.join(out, "story.json"), "w"), indent=1)


def run():
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
    json.dump(results, open(os.path.join(out, "story.json"), "w"))
    for stage in stages[begin:end]:
        frames = bot.game.frames
        battles, ai_moves = len(bot.log), bot.ai_moves
        try:
            stage(bot)
        except Stuck as e:
            results.append(dict(stage=stage.__name__, result="stuck", note=str(e)))
            json.dump(results, open(os.path.join(out, "story.json"), "w"), indent=1)
            print("%-24s STUCK  %s" % (stage.__name__, e), flush=True)
            break
        bot.save(os.path.join(out, "stage_%s.dst" % stage.__name__))
        minutes = (bot.game.frames - frames) / 3600
        results.append(dict(stage=stage.__name__, result="ok", at=bot.where(), game_minutes=round(minutes, 1),
                            battles=len(bot.log) - battles, ai_moves=bot.ai_moves - ai_moves,
                            menu_screens=sum(b["menus"] for b in bot.log[battles:])))
        json.dump(results, open(os.path.join(out, "story.json"), "w"), indent=1)
        print("%-24s ok     at %-28s %5.1f game minutes, %d battles, %d AI moves" % (
            stage.__name__, bot.where(), minutes, len(bot.log) - battles, bot.ai_moves - ai_moves), flush=True)
    json.dump(results, open(os.path.join(out, "story.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
