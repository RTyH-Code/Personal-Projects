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
import random
import struct
import subprocess
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import battle_test
import boulders as boulders_plan
import pkm
import team_sets
import walk_test
from walk_test import DIRS, text_box

TEAM_LEVEL = 16
RETRIES = int(os.environ.get("STORY_RETRIES", "3"))                  # a stage is played again after a lost battle, as a player would, this many times
# up to this many frames of waiting after a stage's start state is loaded. The game's random numbers move on
# every frame, so without it two runs from the same save play every battle out move for move the same
JITTER = int(os.environ.get("STORY_JITTER", "0"))
# heal the party before every boss, standing in for a player's potions (STORY_BOSS_HEAL=0 for the old way)
BOSS_HEAL = os.environ.get("STORY_BOSS_HEAL", "1") != "0"
TEAM = (0, 1, 2, 4)          # of battle_test.REFERENCE: Cyndaquil, Mareep, Geodude and Abra, evolved to the level
FIELD_SYSTEM_AVATAR = 0x40          # FieldSystem.playerAvatar
FIELD_SYSTEM_LOCATION = 0x20        # FieldSystem.location -> {mapId, warpId, x, y, direction}
FIELD_SYSTEM_OBJECTS = 0x3C         # FieldSystem.mapObjectManager -> {flags, objectCount, ..., objects at 0x124}
FOLLOWER = 253                      # object id of the Pokemon that walks behind the player
OBJECT_SIZE = 0x12C                 # LocalMapObject: flags, flags2, id, ..., currentX at 0x64, currentZ at 0x6C
SURF = {0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x19, 0x2A, 0x50, 0x51, 0x52, 0x53, 0x73, 0x78, 0x7C}
WHIRLPOOL = 0x11        # blocked to a step; Whirlpool (HM05, from the bag in the hack) takes the player through
WATERFALL = 0x13        # likewise for Waterfall (HM07): A facing it, and Yes, climbs it
ROCK_CLIMB = 0x4B       # a rocky wall (Mt. Silver): A facing it, and Yes, climbs it with HM08's Rock Climb
FIELD_MOVE_WATER = {WHIRLPOOL, WATERFALL, ROCK_CLIMB}      # crossed by a field move: face it, A, Yes
LEDGES = {0x38: "right", 0x39: "left", 0x3A: "up", 0x3B: "down"}
LADDERS = {0x3C: "up", 0x3D: "down", 0x3E: "down"}
NO_BUTTON = (128, 120)  # "No" of the touch-screen Yes/No buttons
ICE = 0x20              # the player slides across it until something stops them
# Blue's gym floor: arrows that carry the player on, over plain floor and turning at each arrow met, until a
# stop tile or something in the way
ARROWS = {0x40: "right", 0x41: "left", 0x42: "up", 0x43: "down"}
ARROW_STOP = 0x4D
BRIDGE = 0x2E           # an arch: a walkway over it one way, a path under it the other
FLAT_BRIDGES = {"T07GYM0101"}   # where the same tile is a wooden walk the player steps off any side (Erika's gym)
FIELD_OBSTACLES = {"std_field_cut", "std_field_rock_smash", "std_field_strength"}
COUNTER = 0x80          # a shop or reception counter: people behind it are talked to across it
EDGES = {0x6C: "right", 0x6D: "left", 0x6E: "up", 0x6F: "down", 0x62: "right", 0x63: "left",    # warp edges,
         0x64: "up", 0x65: "down", 0x69: "up", 0x5E: "right", 0x5F: "left"}                     # doors, stairs
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}
# holes the player drops through to the floor below, by script (not in the maps' warp lists): (map, tile) ->
# (map, tile landed on). Victory Road 3F's five, from its script (scr_seq_D43R0103_002 to _006)
HOLES = {("D43R0103", (55, 42)): ("D43R0102", (57, 42)), ("D43R0103", (26, 38)): ("D43R0102", (28, 38)),
         ("D43R0103", (29, 44)): ("D43R0102", (31, 44)), ("D43R0103", (20, 18)): ("D43R0102", (22, 17)),
         ("D43R0103", (56, 28)): ("D43R0102", (58, 28))}

# The trainer AI. Each battler gets six controller handlers when a battle opens (overlay 12, 0x02260EA4, called
# with the BattleSystem and the battler's OpponentData): the player's read the touch screen, every other
# battler's run the trainer AI with its trainer's AI flags. The bot hands the player's side the same AI handlers
# and the flags every trainer in the hack has, so the game itself chooses the player's moves and switches.
BATTLER_SETUP = 0x02260EA4
AI_SELECT_MOVE = 0x0221BEF4     # overlay 10: the trainer AI choosing a move for battler r1; counted for the report
AI_HANDLERS = (0x0225E105, 0x0225E405, 0x0225E6FD, 0x0225F3A5, 0x0225F8AD)    # an opponent's, as set up there
BATTLE_TRAINER_IDS = 0xA0     # BattleSystem.trainerId[4]: who each battler belongs to (0 for a wild Pokemon)
BATTLE_CONTEXT, BATTLE_MONS, BATTLE_MON_SIZE, BATTLE_MON_HP = 0x30, 0x2D40, 0xC0, 0x4C   # who is out, HP left
BATTLE_MON_MAX_HP, BATTLE_MON_TYPES = 0x50, 0x24    # and its max HP and two types (moves are four u16 at 0x0C)
BATTLER_ID, BATTLER_IS_AI = 0x194, 0x196          # in OpponentData, after the six handlers at 0
BATTLE_TRAINERS, TRAINER_SIZE, TRAINER_AI_FLAGS = 0xAC, 0x34, 0x0C      # BattleSystem.trainers[4]
# The AI cannot answer "Will you switch your Pokemon?", so the bot plays with the Set battle style, as a player can
# choose in Options: whenever the game reads the style (Options_GetBattleStyle), the bit is set first.
OPTIONS_GET_BATTLE_STYLE, BATTLE_STYLE_SET = 0x0202AD90, 0x40
# hg-engine's own bag functions (build/rom_gen_battle.ld), each called with the bag as its first argument: the bot
# learns where the bag is from them (Bag_GetRegisteredItemSlot1, Bag_GetItemPocket, Bag_GetItemSlotForAdd,
# Bag_GetItemSlotForRemove, Bag_HasItem, Bag_GetQuantity, Bag_AddItem, Bag_GetPocketSlotN)
BAG_FUNCS = (0x023D80BC, 0x023D8128, 0x023D8200, 0x023D8298, 0x023D82BA, 0x023D8344, 0x023D8532, 0x023D8600)
# where the medicine pocket starts in the bag (include/bag.h): items (165 + 32 + 48 Mega Stones), key items (50 + 42),
# TMs and HMs (101) and mail (12), four bytes a slot; 40 slots of medicine, then 64 of berries
BAG_MEDICINE, BAG_MEDICINE_SLOTS, BAG_BERRIES_SLOTS = (245 + 92 + 101 + 12) * 4, 40, 64
EXPERT_AI = 0x7                 # F_PRIORITIZE_SUPER_EFFECTIVE | F_EVALUATE_ATTACKS | F_EXPERT_ATTACKS
TRAINER_ITEMS = 0x04            # Trainer.items[4], after type, class, sprite and party size
# STORY_BATTLE_ITEMS=HYPER_POTION,FULL_HEAL,...: up to four items the player's side carries into each trainer battle,
# as a player carries potions. They go in the player's trainer item slots, which the trainer AI uses by its own
# rules (an opponent trainer's items work the same way); each is used once. Off by default
BATTLE_ITEMS = [i for i in os.environ.get("STORY_BATTLE_ITEMS", "").split(",") if i][:4]
# STORY_SMART=1: the bot plays its own turns as a player would (smart.py): it keeps the player's own command menu,
# party screen and bag, and on each turn fights, switches to a better matchup or uses a potion; once it picks Fight,
# the trainer AI picks the move. Off by default, so earlier results stay comparable.
SMART = os.environ.get("STORY_SMART", "0") == "1"
# the AI handlers left to the player there: commands, the party screen (a switch) and replacements after a faint
SMART_KEEP = [int(x) for x in os.environ.get("STORY_SMART_KEEP", "0,3,4").split(",")]
SMART_POTIONS = int(os.environ.get("STORY_SMART_POTIONS", "6"))


TRAINER_FLAG_BASE = 0x550
BLACKTHORN_GYM, MAGMA = "T30GYM0101", 0x2C     # Clair's gym, and its lava's tile behaviour


class Stuck(Exception):
    pass


class Moved(Stuck):
    """A scene took the player to another map on the way."""


class Bot:
    def __init__(self, rom, tree, dump, out_dir):
        self.out = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self.world = walk_test.World(rom, tree, dump)
        self.data = battle_test.load(tree)
        self.sets = team_sets.Data(tree, dump)
        self.species_names = {v: k for k, v in self.data["species"].items()}
        self.move_names = {v: k for k, v in self.data["boss_teams"].MOVE_IDS.items()}
        self.party_at = None
        self.team = None
        self.game = walk_test.Walker(rom)
        self.names = {v: k for k, v in self.world.map_ids.items()}
        self.fs = None
        self.log = []
        self.last_place = None
        self.surfable = None        # True once the player has Surf
        self.forbidden = {}         # map -> tiles a stage has said never to step on
        self.shut = set()           # (map, warp, from tile) found unreachable where a route expected it; per stage
        self.walls = set()          # (matrix or map, tile, direction) found blocked though the tiles say open
        self.battlers = {}          # battler id -> (BattleSystem, OpponentData) for the battle being opened
        self.game.emu.memory.register_exec(BATTLER_SETUP, self._battler_setup)
        self.game.emu.memory.register_exec(OPTIONS_GET_BATTLE_STYLE, self._set_style)
        self.bag = None
        for address in BAG_FUNCS:
            self.game.emu.memory.register_exec(address, self._bag_seen)
        self.ai_moves = 0           # moves the AI chose for the player's side
        self.ai_battles = self.handed = 0
        self.bsys = None
        self.trainer_ids = []
        self.kos = []               # (battle began by, side that fainted, the Pokemon, the opposing Pokemon out)
        self.battling = False
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
        self.last_place = self.names.get(map_id, str(map_id)), p[1], p[2]
        return self.last_place

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
        """A story flag, by name or number."""
        g = self.game
        f = self.world.flags[name] if isinstance(name, str) else name
        return bool(g.emu.memory.unsigned[g.vars_pointer + walk_test.FLAGS_OFFSET + f // 8] >> (f % 8) & 1)

    def beaten(self, trainer):
        """Whether a trainer (by number) has been beaten: the game keeps a flag for each, from 0x550."""
        return self.flag(TRAINER_FLAG_BASE + trainer)

    def expect(self, name, what):
        """Stop if a story flag that the stage should have set is not set."""
        if not self.flag(name):
            self.stuck("%s did not happen (%s is not set)" % (what, name))

    def facing(self):
        p = self.game.position()
        return {0: "up", 1: "down", 2: "left", 3: "right"}.get(p[3]) if p else None

    # ------------------------------------------------------------- the map

    def tiles(self, code):
        """Walkable tiles of the matrix the map is in: {(x, z): behaviour}. Outdoors this is the whole region.
        In Clair's gym the lava is not walkable, but the floors of its three platforms, wherever they are now,
        are."""
        grid, _ = self.world.grid(self.world.headers[code]["matrix"])
        # whirlpools and waterfalls are blocked to a step but crossed with a field move; and some ledges (Route
        # 45's) carry the blocked bit too, though they are jumped like any other
        out = {p: v & 0xFF for p, v in grid.items()
               if not v & 0x8000 or v & 0xFF in FIELD_MOVE_WATER or v & 0xFF in LEDGES}
        if code == BLACKTHORN_GYM:
            here = self.where()
            out = {p: b for p, b in out.items() if b != MAGMA}
            if here and here[0] == code:
                for platform in self.platforms():
                    for t in platform["floor"]:
                        out[t] = 0
        return out

    def platforms(self):
        """Clair's gym's three platforms, from the game's memory (src/field/gymmick/blackthorn.c in the
        decompilation): each one's 18 floor tiles and its three buttons (rotate, move one way, the other)."""
        g, fs = self.game, self.field_system()
        if not fs:
            return []
        local = g.word(g.word(fs + 4) + 0x24)
        if not local:
            return []
        s32 = lambda a: struct.unpack("<i", struct.pack("<I", g.word(a)))[0]
        point = lambda a: (s32(a), s32(a + 4))
        out = []
        for i in range(3):
            base = local + 4 + 0x270 * i
            out.append(dict(rotate=point(base + 8), left=point(base + 0x10), right=point(base + 0x18),
                            floor=[point(base + 0x1E0 + 8 * j) for j in range(18)]))
        return out

    def people(self, code):
        here = self.where()
        if here and here[0] == code:
            # the walking Pokemon behind the player is no obstacle: the player swaps places with it
            return {p for i, p in self.objects().items() if i != FOLLOWER}
        return {(e["x"], e["z"]) for e in self.world.events(code).get("object_events", [])}

    def ice_blocks(self, code):
        """{object id: tile} of the ice blocks on the map now (Pryce's gym): the player pushes them by sliding
        into them."""
        here = self.where()
        if not here or here[0] != code:
            return {}
        events = self.world.events(code).get("object_events", [])
        return {i: pos for i, pos in self.objects().items()
                if i < len(events) and "_ice" in str(events[i].get("id")) and "TRAINER" not in str(events[i].get("script"))}

    def ice_path(self, code, start, goals, blocked, blocks):
        """Like path, on an ice floor with ice blocks: the player slides until something stops them, and
        sliding into a block pushes it along until it hits something (the player stops where they are). The
        search keeps where the blocks are."""
        tiles = self.tiles(code)
        def free(t, bl):
            b = tiles.get(t)
            return b is not None and b not in SURF and t not in blocked and t not in bl
        first = (start, frozenset(blocks))
        seen = {first: None}
        queue = deque([first])
        while queue:
            state = queue.popleft()
            here, bl = state
            if here in goals:
                steps = []
                while seen[state]:
                    state, d = seen[state]
                    steps.append(d)
                return steps[::-1]
            for d, (dx, dz, _) in DIRS.items():
                pos, nbl = here, bl
                nxt = (pos[0] + dx, pos[1] + dz)
                if nxt in nbl:
                    if tiles.get(pos) != ICE and tiles.get(nxt) != ICE:
                        continue
                    end = nxt                     # push it: it slides until something is in the way
                    while free((end[0] + dx, end[1] + dz), nbl) and tiles.get(end) == ICE:
                        end = (end[0] + dx, end[1] + dz)
                    if end == nxt:
                        continue
                    nbl = (nbl - {nxt}) | {end}
                elif free(nxt, nbl):
                    pos = nxt
                    while tiles.get(pos) == ICE:
                        n2 = (pos[0] + dx, pos[1] + dz)
                        if n2 in nbl:
                            end = n2
                            while free((end[0] + dx, end[1] + dz), nbl) and tiles.get(end) == ICE:
                                end = (end[0] + dx, end[1] + dz)
                            if end != n2:
                                nbl = (nbl - {n2}) | {end}
                            break
                        if not free(n2, nbl):
                            break
                        pos = n2
                else:
                    continue
                state2 = (pos, nbl)
                if state2 not in seen:
                    seen[state2] = (state, d)
                    queue.append(state2)
        return None

    def path(self, code, start, goals, avoid=frozenset()):
        """Shortest list of directions from start to any goal tile, or None.

        An arch (BRIDGE tile) is two places at once: the walkway over it and the path beneath it, at right
        angles. Whichever way the player comes onto one, it leaves the same way, so the search keeps, for a
        bridge tile, the axis it was entered along."""
        tiles = self.tiles(code)
        surf = self.can_surf()
        matrix = self.world.headers[code]["matrix"] or code
        warps = {(w["x"], w["z"]) for m in self.region_maps(code) for w in self.world.events(m).get("warp_events", [])}
        # don't walk into a warp on the way; a goal tile someone stands on (or was in the way at) can't be reached;
        # and keep off any tiles a stage has ruled out on this map (forbid)
        blocked = self.people(code) | set(avoid) | (warps - set(goals)) | self.forbidden.get(code, set())
        blocked |= {t for (m, t) in HOLES if m == code} - set(goals)      # never drop through one by accident
        on_ladder = LADDERS.get(tiles.get(start))
        blocks = self.ice_blocks(code)
        if any(b == ICE for b in tiles.values()):     # slides (and, in Pryce's gym, ice blocks pushed)
            return self.ice_path(code, start, set(goals), blocked - set(blocks.values()), blocks.values())
        axis = lambda d: "h" if d in ("left", "right") else "v"
        first = (start, None)
        seen = {first: None}
        queue = deque([first])
        while queue:
            state = queue.popleft()
            here, along = state
            if here in goals:
                steps = []
                while seen[state]:
                    state, d = seen[state]
                    steps.append(d)
                return steps[::-1]
            for d, (dx, dz, _) in DIRS.items():
                if here == start and d == on_ladder:
                    continue                       # that would climb the ladder just arrived by
                if along and axis(d) != along:
                    continue                       # on an arch: over it or under it, never off the side
                if (matrix, here, d) in self.walls:
                    continue                       # found not to be passable (a drop the tiles don't show)
                nxt = (here[0] + dx, here[1] + dz)
                b = tiles.get(nxt)
                if b is None or (b in SURF and not surf) or nxt in blocked:
                    continue
                if b in LEDGES:
                    if LEDGES[b] != d:
                        continue
                    nxt = (nxt[0] + dx, nxt[1] + dz)   # a ledge is jumped in one move
                    if tiles.get(nxt) is None:
                        continue
                    b = tiles.get(nxt)
                if b == ICE:
                    # on ice the player slides on until a wall, someone, or plain floor stops them
                    while tiles.get(nxt) == ICE:
                        n2 = (nxt[0] + dx, nxt[1] + dz)
                        b2 = tiles.get(n2)
                        if b2 is None or b2 in SURF or n2 in blocked:
                            break
                        nxt = n2
                    b = tiles.get(nxt)
                if b in ARROWS:
                    way, moves = ARROWS[b], 0
                    while moves < 200:
                        moves += 1
                        ax, az, _ = DIRS[way]
                        n2 = (nxt[0] + ax, nxt[1] + az)
                        b2 = tiles.get(n2)
                        if b2 is None or n2 in blocked:
                            break
                        nxt = n2
                        if b2 == ARROW_STOP:
                            break
                        way = ARROWS.get(b2, way)
                    if moves >= 200:
                        continue                   # round and round: never stops
                    b = tiles.get(nxt)
                state2 = (nxt, axis(d) if b == BRIDGE and code not in FLAT_BRIDGES else None)
                if state2 in seen:
                    continue
                seen[state2] = (state, d)
                queue.append(state2)
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
                image = g.emu.screenshot()
                if self.flash(image):
                    calm = 0                    # the screen fading to or from white: a scene going on
                    g.run(20)
                    frames += 20
                    continue
                if text_box(image):
                    calm = 0
                    if answers and not self.question():
                        g.run_every_frame(30)               # the Yes/No buttons may be about to appear
                    answer = answers.pop(0) if answers and self.question() else "a"
                    if answer == "b":
                        g.touch(*NO_BUTTON, after=20)     # the Yes/No buttons are on the touch screen
                    else:
                        g.key("a", after=20)
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

    def walk(self, code, goals, avoid=(), face=None, leave_ok=False, never=()):
        """Walk to one of the goal tiles of the map, dealing with whatever happens on the way. With leave_ok,
        reaching another map instead (a warp on the goal tile) also ends the walk, returning None."""
        goals = {tuple(g) for g in goals}
        avoid = set(avoid)
        forgets = waits = 0
        for attempt in range(250):
            self.settle()
            here = self.where()
            if not here:
                continue
            if here[0] != code and not self.same_region(here[0], code):
                if leave_ok:
                    return None
                raise Moved("on %s, not %s" % (here[0], code))
            pos = (here[1], here[2])
            if pos in goals:
                if face and self.facing() != face:
                    self.game.key(face, hold=2, after=10)
                return pos
            never = set(never)                # tiles never to step on (a drop in a dark gym)
            route = self.path(here[0], pos, goals, avoid | never)
            if route is None and avoid:
                avoid = set()                 # whoever was in the way may have moved on
                route = self.path(here[0], pos, goals, never)
            key = self.world.headers[here[0]]["matrix"] or here[0]
            if route is None and forgets < 3 and any(w[0] == key for w in self.walls):
                # a step can fail for other reasons (a trainer about to come over): forget what was learned
                forgets += 1
                self.walls = {w for w in self.walls if w[0] != key}
                route = self.path(here[0], pos, goals, avoid | never)
            if route is None and waits < 10:
                # someone may be standing in the way for a moment (Bill at Ecruteak's counter): wait and look again
                waits += 1
                self.game.run(60)
                continue
            if route is None:
                self.stuck("no path on %s from %s to %s" % (here[0], pos, sorted(goals)[:4]))
            tiles_here = self.tiles(here[0])
            for d in route:
                p = self.game.position()
                dx, dz, _ = DIRS[d]
                if p and (ICE in (tiles_here.get((p[1], p[2])), tiles_here.get((p[1] + dx, p[2] + dz)))
                          or tiles_here.get((p[1] + dx, p[2] + dz)) in ARROWS):
                    # a slide: one move, wait for the player to stop, and plan again from wherever that is
                    self.game.key(d, hold=6, after=10)
                    last = None
                    for _ in range(60):
                        q = self.game.position()
                        if q and last and q[1:3] == last[1:3]:
                            break
                        last = q
                        self.game.run(8)
                    break
                if p and tiles_here.get((p[1] + dx, p[2] + dz)) in FIELD_MOVE_WATER:
                    # a whirlpool or a waterfall: face it, A, and Yes to Whirlpool or Waterfall; then plan again
                    # from wherever it leaves us
                    for hold in (2, 4, 8):        # a short press may not turn the player (in tall grass)
                        self.game.key(d, hold=hold, after=10)
                        if self.facing() == d:
                            break
                    self.game.key("a", after=30)
                    self.settle(["a"])
                    break
                if self.surf_needed(here[0], d):
                    if not self.start_surf(d):
                        break
                    continue
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
                        ahead = (cur[1] + dx, cur[2] + dz)
                        if ahead in self.people(cur[0]):
                            avoid.add(ahead)                  # someone in the way
                        elif self.tiles(cur[0]).get((cur[1], cur[2])) != BRIDGE:
                            # nobody there, yet the step fails: the floor changes height where the tiles
                            # don't say so (a raised walkway). Remember it and find another way
                            self.walls.add((self.world.headers[cur[0]]["matrix"] or cur[0], (cur[1], cur[2]), d))
                    break
        self.stuck("could not reach %s on %s" % (sorted(goals)[:4], code))

    def boulders(self, code):
        """{object id: tile} of the Strength boulders on the map now."""
        events = self.world.events(code).get("object_events", [])
        return {i: pos for i, pos in self.objects().items()
                if i < len(events) and events[i].get("script") == "std_field_strength"}

    def drop_boulders(self, code, holes, goals=None, need_all=True):
        """Push every Strength boulder the player can get to into one of the holes (boulders.py plans it),
        then walk to one of the goals. The first push uses Strength (A at the boulder, then Yes); after each
        move the bot checks the game against the plan, and plans again from wherever things are."""
        holes = set(holes)
        strength = False
        # every wild Pokemon, and every push that leaves the player somewhere the plan didn't expect, means a
        # new plan: give up only when many plans in a row get nowhere
        progress, idle = None, 0
        for attempt in range(1000):
            self.settle()
            now = (self.where(), tuple(sorted(self.boulders(code).values())))
            idle = idle + 1 if now == progress else 0
            progress = now
            if idle >= 30:
                break
            here = self.where()
            if not here or here[0] != code:
                self.stuck("left %s while pushing boulders" % code)
            pos = (here[1], here[2])
            people = self.people(code)
            boulders = set(self.boulders(code).values())
            warps = {(w["x"], w["z"]) for w in self.world.events(code).get("warp_events", [])}
            floor = set(self.tiles(code)) - holes - warps - (people - boulders) | set(goals or ())
            # only the boulders next to where the player can walk
            area = self.reach(code, pos)
            mine = {b for b in boulders if any((b[0] + dx, b[1] + dz) in area for dx, dz, _ in DIRS.values())}
            if need_all:
                moves = boulders_plan.plan_one_by_one(floor - (boulders - mine), pos, mine, holes, goals)
            else:
                moves = boulders_plan.plan(floor - (boulders - mine), pos, mine, holes, goals, need_all=False)
            if moves is None:
                self.stuck("no way to push the boulders on %s into the holes" % code)
            if not moves:
                return
            # the plan's first push: where to stand and which way. The walking between pushes is left to walk(),
            # which knows the arches and bridges the plan's flood fill doesn't
            at, push = pos, None
            for d in moves:
                dx, dz, _ = DIRS[d]
                nxt = (at[0] + dx, at[1] + dz)
                if nxt in mine:
                    push = d
                    break
                at = nxt
            if push is None:
                self.walk(code, list(goals) if goals else [at])
                return
            if at != pos:
                try:
                    self.walk(code, [at])
                except Stuck as e:
                    if str(e).startswith("lost a battle"):
                        raise
                    continue
            if not strength:
                # face it and press A: "This boulder looks like it can be pushed... use Strength?"
                for hold in (2, 3, 4):
                    self.game.key(push, hold=hold, after=10)
                    if self.facing() == push:
                        break
                self.game.key("a", after=30)
                self.settle(["a"])
                strength = True
            self.game.key(push, hold=16, after=40)
            self.settle()
        self.stuck("could not push the boulders on %s" % code)

    def same_region(self, a, b):
        return self.world.headers[a]["matrix"] == self.world.headers[b]["matrix"] == 0

    def go_through(self, code, warp_index, into=None):
        """Use a warp of the map: walk onto it (a door or stairs) and, for warps at the edge of a room, keep
        walking `into` it. Waits until the next map has loaded. A trainer who spots the player on the last step
        (Proton at the Radio Tower's 4F stairs) stops the warp: the scene and battle are seen through, and the
        warp is tried again."""
        for attempt in range(3):
            try:
                return self._go_through(code, warp_index, into)
            except Stuck:
                here = self.where()
                if attempt == 2 or not here or here[0] != code:
                    raise
                self.settle()

    def _go_through(self, code, warp_index, into=None):
        warp = self.world.events(code)["warp_events"][warp_index]
        tile = (warp["x"], warp["z"])
        # a warp to somewhere else on the same map (Diglett's Cave's ladders): the map doesn't change, so it has
        # worked once the player stands at (or just off) the warp it leads to
        if warp["dest_header_id"] == "MAP_" + code:
            dest = self.world.events(code)["warp_events"][warp["dest_warp_id"]]
            dest = (dest["x"], dest["z"])
            arrived = self.arrived

            def same_map_arrived(old, frames=400):
                for _ in range(frames // 10):
                    self.game.run(10)
                    here = self.where()
                    if here and here[0] == code and abs(here[1] - dest[0]) + abs(here[2] - dest[1]) <= 1:
                        self.settle()
                        return True
                return arrived(old, frames) if frames > 0 else False
            self.arrived = same_map_arrived
            try:
                return self._go_through_warp(code, warp_index, into, warp, tile)
            except Stuck:
                # the walk onto it can end in a "no path" once the warp has moved the player on: that's success
                here = self.where()
                if here and here[0] == code and abs(here[1] - dest[0]) + abs(here[2] - dest[1]) <= 1:
                    self.settle()
                    return
                raise
            finally:
                self.arrived = arrived
        return self._go_through_warp(code, warp_index, into, warp, tile)

    def _go_through_warp(self, code, warp_index, into, warp, tile):
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
            # a wide doorway is several warps to the same place: stand before whichever is easiest to reach
            goals = [(tile[0] - dx, tile[1] - dz)]
            for i, other in enumerate(self.world.events(code)["warp_events"]):
                # only the warps beside this one (a doorway two tiles wide): a map can have other ways to the
                # same map that lead somewhere else in it
                if (i != warp_index and other["dest_header_id"] == warp["dest_header_id"]
                        and abs(other["x"] - warp["x"]) + abs(other["z"] - warp["z"]) <= 2):
                    e, d = self.warp_entry(code, i)
                    if d == into and e != (other["x"], other["z"]):
                        goals.append(e)
            self.walk(code, goals)
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
        into = EDGES.get(grid.get(tile, 0) & 0xFF)
        if into:
            dx, dz, _ = DIRS[into]
            return (tile[0] - dx, tile[1] - dz), into
        ladder = LADDERS.get(grid.get(tile, 0) & 0xFF)
        if ladder:
            return tile, ladder                  # stand on the ladder and climb it
        # some maps put the warp on the plain tile in front of a doorway: walk on into the doorway from it
        for d, (dx, dz, _) in DIRS.items():
            if EDGES.get(grid.get((tile[0] + dx, tile[1] + dz), 0) & 0xFF) == d:
                return tile, d
        return tile, None

    def forbid(self, code, tiles):
        """Never step on these tiles of the map, on any walk from now on (alarms, drops)."""
        self.forbidden.setdefault(code, set()).update(tiles)

    def can_surf(self):
        """Whether the player can surf: with the hack, HM03 in the bag is enough once the Fog Badge is won."""
        if self.surfable is None:
            try:
                self.surfable = self.flag("FLAG_GOT_HM03")
            except (KeyError, TypeError):
                return False
            if not self.surfable:
                self.surfable = None
                return False
        return True

    def surf_needed(self, code, d):
        """Whether stepping that way goes from land onto water (which takes Surf, not a step)."""
        p = self.game.position()
        if not p or not self.can_surf():
            return False
        tiles = self.tiles(code)
        dx, dz, _ = DIRS[d]
        return tiles.get((p[1], p[2])) not in SURF and tiles.get((p[1] + dx, p[2] + dz)) in SURF

    def start_surf(self, d):
        """Face the water, press A and say Yes to Surf; the player hops onto the water."""
        g = self.game
        before = g.position()
        g.key(d, hold=2, after=10)
        g.key("a", after=30)
        self.settle(["a"])
        for _ in range(30):
            p = g.position()
            if p and before and p[1:3] != before[1:3]:
                return True
            g.run(10)
        return False

    def obstacles(self, code):
        """Tiles of the map's objects that are there now and stand in the way: everything but trainers."""
        here = self.where()
        stands = lambda script: script in FIELD_OBSTACLES or "trainer" not in script
        if not here or here[0] != code and not self.same_region(here[0], code):
            # another map: only its Cut trees, rocks and boulders are sure to be there. Doors and people come and
            # go by script (the Hideout's password door), so the event data can't say; a route that turns out
            # to be shut is learnt when walked (see travel)
            out = set()
            for e in self.world.events(code).get("object_events", []):
                flag = e.get("hidden_flag")
                try:
                    if flag and flag != "FLAG_NOTHING" and self.flag(flag):
                        continue
                except (KeyError, TypeError):
                    pass
                if str(e.get("script")) in FIELD_OBSTACLES:
                    out.add((e["x"], e["z"]))
            return out
        events = self.world.events(here[0]).get("object_events", [])
        out = set()
        for i, pos in self.objects().items():
            if i >= len(events):
                continue
            script = str(events[i].get("script"))
            # Cut trees, rocks and boulders; and anything else that is not a trainer (trainers come to the
            # player): doors like the Hideout's password doors, item balls, people standing in the way
            if stands(script):
                out.add(pos)
        return out

    def reach(self, code, start):
        """Every tile of the map (or outdoor region) the player can walk to from start, with its distance."""
        tiles = self.tiles(code)
        surf = self.can_surf()
        blocked = self.obstacles(code)
        seen = {start: 0}
        queue = deque([start])
        while queue:
            here = queue.popleft()
            for d, (dx, dz, _) in DIRS.items():
                nxt = (here[0] + dx, here[1] + dz)
                b = tiles.get(nxt)
                if b is None or (b in SURF and not surf) or nxt in blocked:
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

    def route(self, target, near=None):
        """The warps to take, [(map, warp index)], to get from here to the target map, fewest steps first. With
        near (a tile of the target map), to the part of the map from which that tile can be walked to."""
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
            if code == target and (near is None or near in self.reach(code, pos)):
                return best[node][1]
            if len(done) > 8000:
                break
            # one flood fill for each walkable stretch: outdoors, many doors lead back to the same one
            key = self.world.headers[code]["matrix"] or code if code in self.world.headers else code
            dist = next((d for k, d in areas if k == key and pos in d), None)
            if dist is None:
                dist = self.reach(code, pos)
                areas.append((key, dist))
            if self.region_tiles(code, target, dist):
                return best[node][1]
            for (m, tile), landing in HOLES.items():
                if m == code and tile in dist:
                    c = cost + dist[tile] + 10
                    if landing not in best or c < best[landing][0]:
                        best[landing] = (c, best[node][1] + [(m, tile)])
                        counter += 1
                        heapq.heappush(queue, (c, counter, landing))
            for m in self.region_maps(code):
                for i, warp in enumerate(self.world.events(m).get("warp_events", [])):
                    if (m, i, pos) in self.shut:
                        continue                # tried from here, and this side of the map does not lead there
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

    # where each town's pin is on the Fly map's touch screen, by the town's map code. The map shows the region
    # the player is in: Johto, or Kanto (towns T01-T11, routes R01-R28)
    KANTO_PINS = {"T01": (116, 107), "T02": (112, 80), "T03": (120, 38), "T04": (183, 45), "T05": (212, 75),
                  "T06": (182, 97), "T07": (160, 80), "T08": (160, 118), "T09": (116, 139), "T10": (84, 68),
                  "T11": (183, 72)}
    FLY_PINS = {"T20": (152, 116), "T21": (120, 116), "T22": (103, 78), "T23": (88, 132), "T25": (68, 103),
                "T27": (80, 55), "T26": (55, 78), "T24": (30, 105), "T28": (116, 60), "T29": (116, 30),
                "T30": (152, 55)}

    def fly(self, town):
        """Fly to a town visited before, as a player would: the start menu, POKEMON, a Pokemon's Fly (this hack
        shows it without the move taught, once HM02 and the Storm Badge are had), then the town's pin on the
        map. Only towns visited have a pin."""
        old = self.where()
        kanto = lambda code: code[:1] in "TR" and code[1:3].isdigit() and int(code[1:3]) <= (11 if code[0] == "T" else 28)
        pins = self.KANTO_PINS if old and kanto(old[0]) else self.FLY_PINS
        if town not in pins:
            self.stuck("no Fly map pin is known for %s on the %s map" % (town, "Kanto" if pins is self.KANTO_PINS
                                                                       else "Johto"))
        self.settle()
        g = self.game
        # which Pokemon the menu shows Fly on: the first that could learn it, or else the first in the party
        # (even fainted). A Pokemon that can't be read is taken not to learn it
        names = {v: k for k, v in self.sets.species_ids.items()}
        learnsets = self.sets.bt.LEARNSETS
        slot = 0
        for i, m in enumerate(self.party_mons()):
            if m.valid() and not m.is_egg and "MOVE_FLY" in learnsets.get(
                    "SPECIES_" + names.get(m.species, ""), {}).get("MachineMoves", []):
                slot = i
                break
        for _ in range(4):
            g.run(30)
            g.key("x", after=70)           # the menu slides in: a touch too soon lands on the wrong icon
            # POKEMON, by touch (the menu's cursor is wherever it was left). A touch can only pick it out, so
            # touch again if the party screen (a pale cyan background at its left edge, which takes a few seconds
            # to come up) hasn't started to show. Anything else (the Bag, say): back out and try again
            def party_screen():
                r, gr, b = g.emu.screenshot().convert("RGB").getpixel((5, 192 + 100))
                return r < 190 and gr > 170 and b > 180
            def wait_party(frames):
                for _ in range(frames // 10):
                    g.run(10)
                    if party_screen():
                        return True
                return False
            g.touch(36, 72, after=10)
            opened = wait_party(100)
            if not opened and g.in_field():     # still the menu, with POKEMON only picked out
                g.touch(36, 72, after=10)
            opened = opened or wait_party(400)
            if opened:
                g.run(30)
                break
            for _ in range(4):
                if g.in_field() and self.free():
                    break
                g.key("b", after=40)
        else:
            self.stuck("the party screen did not open for Fly")
        # the party sits in two columns of three, the right one a little lower: touch the Pokemon's panel, then
        # Fly, the first of its field moves, at the top left of its menu. A touch while a screen is still coming
        # up only picks a button out, so each is touched until the next screen shows: the menu by its orange Fly
        # button at (40, 30), the map by that button being gone
        def fly_button():
            r, gr, b = g.emu.screenshot().convert("RGB").getpixel((40, 192 + 30))
            return r > 220 and 160 <= gr <= 220 and b < 100
        panel = (64 if slot % 2 == 0 else 190, 30 + 48 * (slot // 2) + 10 * (slot % 2))
        for step, want in ((panel, True), ((64, 32), False)):
            for _ in range(3):
                g.touch(*step, after=10)
                for _ in range(20):
                    g.run(10)
                    if fly_button() == want:
                        break
                if fly_button() == want:
                    break
        g.run(60)
        g.touch(*pins[town], after=40)
        g.key("a", after=60)
        for _ in range(60):
            g.run(10)
            here = self.where()
            if here and here[0] == town and g.in_field() and self.free():
                self.settle()
                return
        g.shot(os.path.join(self.out, "fly.png"))
        self.stuck("Fly from %s to %s did not get there" % (old and old[0], town))

    def travel(self, target, near=None):
        """Go to the target map by whatever warps lead there; outdoors, on until the player stands in it. With
        near, to the part of the map that tile is in (a map can be in parts joined only through other maps)."""
        cut = False
        for attempt in range(6):
            here = self.where()
            if near and here and here[0] == target and near in self.reach(target, (here[1], here[2])):
                return
            try:
                steps = self.route(target, near)
            except Stuck:
                # a Cut tree may stand in the way (Celadon's gym): cut those the player can get to, and look again
                if not cut and here and self.cut_trees(here[0]):
                    cut = True
                    continue
                if attempt >= 2:
                    raise
                # just after a map loads, its people and doors are still being set out: look again shortly
                self.game.run(60)
                continue
            try:
                for code, index in steps:
                    here = self.where()
                    if isinstance(index, tuple):        # a hole: walk onto it and drop
                        self.walk(code, [index], leave_ok=True)
                        self.settle()
                        continue
                    try:
                        self.go_through(code, index)
                    except Stuck as e:
                        if isinstance(e, Moved):
                            raise
                        # a Cut tree may stand in the way (Route 2): cut what can be reached and plan again
                        cur = self.where()
                        if not cut and cur and self.cut_trees(cur[0]):
                            cut = True
                            raise Moved(str(e))
                        if "no path" not in str(e):
                            raise
                        # the warp can't be reached from here after all (a door shut by script): plan round it
                        self.shut.add((code, index, (here[1], here[2]) if here else None))
                        raise Moved(str(e))
            except Moved:
                continue                    # plan again from where the scene left the player
            here = self.where()
            if here and here[0] != target:
                dist = self.reach(here[0], (here[1], here[2]))
                goals = self.region_tiles(here[0], target, dist)
                if goals:
                    try:
                        self.walk(target, [min(goals, key=dist.get)])
                    except Moved:
                        continue
                    here = self.where()
            if here and here[0] == target and (near is None or near in self.reach(target, (here[1], here[2]))):
                return
        self.stuck("did not get to %s" % target)

    def cut_trees(self, code):
        """Cut every Cut tree on this map the player can walk up to (A, and Yes: this hack lets Cut work untaught
        once HM01 and the Hive Badge are had). True if any was cut."""
        events = self.world.events(code).get("object_events", [])
        done = False
        while True:             # each tree cut can open the way to another (Route 2 has three in a row)
            progress = False
            for i in [i for i in sorted(self.objects())
                      if i < len(events) and str(events[i].get("script")) == "std_field_cut"]:
                try:
                    self.talk(code, i)
                except Stuck as e:
                    if "no path" not in str(e) and "could not reach" not in str(e):
                        raise
                if i not in self.objects():
                    done = progress = True
            if not progress:
                return done

    def arrived(self, old, frames=400):
        for _ in range(frames // 10):
            self.game.run(10)
            here = self.where()
            if here and here[0] != old and self.free():
                return True
        return False

    def expect_item(self, name, what):
        """Stop if an item that the stage should have put in the bag never went in."""
        item = self.data["items"][name]
        if not any(i == item for i, _ in self.game.added):
            self.stuck("%s did not happen (no %s went into the bag)" % (what, name))

    def talk(self, code, target, answers=(), never=(), boss=None):
        """Stand next to a person or thing and press A facing it; then see the scene through. `target` is a tile
        (x, z), or the number of a person in the map's list of object events, wherever they now stand. With
        boss (a name), the harness heals the party once the player stands by them, before A: a player would use
        potions before a boss, and the bot can't (BOSS_HEAL=0 turns it off)"""
        if isinstance(target, int):
            self.settle()
            people = self.objects()
            if target not in people:
                self.stuck("person %d is not on %s" % (target, code))
            target = people[target]
        options = {}
        grid = self.world.grid(self.world.headers[code]["matrix"])[0]
        for d, (dx, dz, _) in DIRS.items():
            near = (target[0] - dx, target[1] - dz)
            options[near] = d
            if grid.get(near, 0) & 0xFF == COUNTER:
                options[(near[0] - dx, near[1] - dz)] = d     # across a counter
        tiles = self.tiles(code)
        options = {t: d for t, d in options.items() if t in tiles}
        for _ in range(5):
            pos = self.walk(code, options, avoid={target}, never=never)
            # a wild Pokemon can jump out on the last step: see it off, and make sure the player is still there
            self.settle()
            here = self.where()
            if here and (here[1], here[2]) == pos:
                break
        if boss and BOSS_HEAL:
            self.restore_party("before %s" % boss)
        # turn to face it: a short press turns without stepping, but now and then it does not register
        for hold in (2, 3, 4, 4):
            self.game.key(options[pos], hold=hold, after=10)
            if self.facing() == options[pos]:
                break
        self.game.key("a", after=30)
        self.settle(answers)

    # ------------------------------------------------------------- battles

    def in_battle(self):
        # a battle has set up its battlers since the last one ended; with the AI playing, no menu need show
        if self.battling and not self.game.in_field():
            return True
        return battle_test.screen_state(self.game.emu.screenshot()) != "other" or self.battle_screen()

    def battle_screen(self):
        image = self.game.emu.screenshot()
        r, g, b = image.getpixel((128, 192 + 55))[:3]
        return r > 190 and g < 110 and b < 120

    def _battler_setup(self, address, size):
        r = self.game.emu.memory.register_arm9
        battler = self.game.emu.memory.unsigned[(r.r1 & 0xFFFFFFFF) + BATTLER_ID]
        self.battling = True
        self.bsys = r.r0 & 0xFFFFFFFF
        self.battlers[battler] = (r.r0 & 0xFFFFFFFF, r.r1 & 0xFFFFFFFF)
        # the game sets up battlers in order, so when an opponent's turn comes, the player's battler before it
        # is done: hand it to the AI now, before the first turn's menu exists
        if battler & 1 and battler - 1 in self.battlers:
            self.give_ai(*self.battlers[battler - 1], battler - 1)
            self.battlers.pop(battler - 1)

    def _ai_move(self, address, size):
        if self.game.emu.memory.register_arm9.r1 & 0xFF in (0, 2):
            self.ai_moves += 1

    def _set_style(self, address, size):
        options = self.game.emu.memory.register_arm9.r0 & 0xFFFFFFFF
        self.game.emu.memory.unsigned[options] |= BATTLE_STYLE_SET

    def hand_to_ai(self):
        """Give the player's battlers the trainer AI: an opposing battler's handlers, and the expert AI flags."""
        g, mem = self.game, self.game.emu.memory.unsigned
        if self.ai_battles != self.handed:
            self.handed = self.ai_battles
            self.battlers = {}
            return True
        if 0 not in self.battlers or 1 not in self.battlers:
            return False
        for mine, theirs in ((0, 1), (2, 3)):
            if mine in self.battlers and theirs in self.battlers:
                self.give_ai(*self.battlers[mine], mine)
        self.battlers = {}
        return True

    def give_ai(self, bsys, od, battler):
        mem = self.game.emu.memory.unsigned
        # the first five handlers: commands, moves, targets, items, replacements. The sixth, the player's yes/no
        # (forget a move to learn a new one?), stays the player's: the AI's never answers it
        for i, value in enumerate(AI_HANDLERS):
            if SMART and i in SMART_KEEP:
                continue                    # the command menu stays the player's: the bot chooses there
            for j in range(4):
                mem[od + 4 * i + j] = (value >> (8 * j)) & 0xFF
        mem[od + BATTLER_IS_AI] = 1
        at = bsys + BATTLE_TRAINERS + TRAINER_SIZE * battler + TRAINER_AI_FLAGS
        for j in range(4):
            mem[at + j] = (EXPERT_AI >> (8 * j)) & 0xFF
        if BATTLE_ITEMS and any(mem[bsys + BATTLE_TRAINER_IDS + 2 * b] | mem[bsys + BATTLE_TRAINER_IDS + 2 * b + 1]
                                for b in (1, 3)):
            at = bsys + BATTLE_TRAINERS + TRAINER_SIZE * battler + TRAINER_ITEMS
            for k in range(4):
                item = self.data["items"][BATTLE_ITEMS[k]] if k < len(BATTLE_ITEMS) else 0
                mem[at + 2 * k], mem[at + 2 * k + 1] = item & 0xFF, item >> 8
        self.ai_battles += 1

    def battle_mons(self):
        """{battler: (species, HP)} of the Pokemon out in the battle now, or {}."""
        g = self.game
        if not self.bsys:
            return {}
        ctx = g.word(self.bsys + BATTLE_CONTEXT)
        if not 0x02000000 <= ctx < 0x02400000:
            return {}
        out = {}
        for b in range(4):
            at = ctx + BATTLE_MONS + BATTLE_MON_SIZE * b
            species = g.emu.memory.unsigned[at] | g.emu.memory.unsigned[at + 1] << 8
            if species:
                out[b] = (species, g.word(at + BATTLE_MON_HP))
        return out

    def watch_kos(self, start, last):
        """Note each Pokemon that has just fainted, and the opposing Pokemon that was out when it did."""
        now = self.battle_mons()
        names = self.species_names
        done = {(k[1], k[2]) for k in self.kos[getattr(self, "first_ko", 0):]}
        # as a battle ends its memory is let go, and what is read there after is no Pokemon: only real species count
        now = {b: v for b, v in now.items() if v[0] in names}
        for b, (species, hp) in now.items():
            before = last.get(b)
            side = "player" if b % 2 == 0 else "opponent"
            # the player's Pokemon changed while the one before still had HP: a switch, not a replacement
            if side == "player" and before and before[0] != species and before[1] > 0 and hp > 0:
                self.switches.append((names.get(before[0], before[0]), names.get(species, species)))
                print("  switch: %s out, %s in" % self.switches[-1], flush=True)
            # fainted since the last look: seen with HP left; or sent out and knocked out before the next look
            # (seen fainted, not seen alive, and not yet counted)
            if hp == 0 and (before and before[0] == species and before[1] > 0
                            or (not before or before[0] != species) and (side, names.get(species, species)) not in done):
                foe = now.get(b ^ 1) or last.get(b ^ 1)
                if side == "player":
                    self.smart_hp[names.get(species, species)] = 0
                self.kos.append((start, side, names.get(species, species), names.get(foe[0], foe[0]) if foe else None))
                print("  KO: %s's %s fainted, %s out" % (side, names.get(species, species),
                                                         names.get(foe[0], foe[0]) if foe else "nobody"), flush=True)
        return now or last

    def record_battle(self, start, result, frames, moves, kos):
        """Append the battle to OUT/battles.jsonl: who, where, with which team, the result and every KO. The file
        grows over runs, for working out later how hard each boss is (and how many Pokemon a win costs)."""
        g = self.game
        ids = self.trainer_ids
        trainers = [dict(id=i, name=self.data["trainers"].get(i, {}).get("name"),
                         cls=self.data["trainers"].get(i, {}).get("cls")) for i in ids if i]
        entry = dict(at=list(start) if start else None, trainers=trainers, wild=not trainers, team=self.team,
                     result=result, game_minutes=round(frames / 3600, 2), ai_moves=moves,
                     kos=[dict(side=side, fainted=who, by=by) for _, side, who, by in kos],
                     switches=[list(x) for x in getattr(self, "switches", [])],
                     choices=getattr(self, "choices", []) if SMART else None,
                     items=BATTLE_ITEMS, items_used=getattr(self, "items_used", None))
        with open(os.path.join(self.out, "battles.jsonl"), "a") as f:
            f.write(json.dumps(entry) + "\n")

    def _bag_looks_right(self, bag):
        """Whether the pockets look right at this address: medicine slots empty or an item and a count, berry
        slots empty or a berry, and something in one of them."""
        if not 0x02000000 <= bag < 0x023F0000:
            return False
        mem = self.game.emu.memory.unsigned
        slot = lambda a: (mem[a] | mem[a + 1] << 8, mem[a + 2] | mem[a + 3] << 8)
        med = [slot(bag + BAG_MEDICINE + 4 * k) for k in range(BAG_MEDICINE_SLOTS)]
        ber = [slot(bag + BAG_MEDICINE + 4 * (BAG_MEDICINE_SLOTS + k)) for k in range(BAG_BERRIES_SLOTS)]
        return all(s == (0, 0) or 0 < s[0] < 1000 and 0 < s[1] < 1000 for s in med) and \
            all(s == (0, 0) or 149 <= s[0] <= 212 and 0 < s[1] < 1000 for s in ber) and \
            any(s != (0, 0) for s in med + ber)

    def _bag_seen(self, address, size):
        """A bag function was called outside battle (in battle they may be given the battle's own copy of the
        bag): its first argument is the bag, if the pockets look right there. Kept in OUT/bag.json for a later
        run from this run's saves."""
        if self.bag or self.battling:
            return
        bag = self.game.emu.memory.register_arm9.r0 & 0xFFFFFFFF
        if self._bag_looks_right(bag):
            self.bag = bag
            json.dump(bag, open(os.path.join(self.out, "bag.json"), "w"))
            print("  the bag is at %08x" % bag, flush=True)

    def find_bag(self):
        """The bag's address: as the game showed it (_bag_seen), or as an earlier run from these saves found it,
        if the pockets still look right there. The bot doesn't open the bag itself: pressing through the field
        menu goes wrong in too many places (a conversation, surfing). Until it is known, the bot has no potions."""
        if not self.bag:
            path = os.path.join(self.out, "bag.json")
            if os.path.exists(path) and self._bag_looks_right(json.load(open(path))):
                self.bag = json.load(open(path))
        return self.bag

    @staticmethod
    def flash(image):
        """Whether the top screen is almost all white: a scene fading to or from white (the Lighthouse's Ampharos
        cured), which text_box, wanting a message box's border, no longer takes for a message."""
        top = image.crop((0, 0, 256, 192)).convert("L")
        return sum(1 for v in top.getdata() if v > 240) > 0.95 * 256 * 192

    def has_pokemon(self):
        """Whether the party has a Pokemon yet (before the starter there is no party to find)."""
        # by the count, not by reading a Pokemon: the game keeps the one walking behind the player decrypted in
        # place much of the time, and early on it is the only one
        try:
            return self.game.word(self.party() + 4) > 0
        except Stuck:
            return False

    def restock_field(self):
        """Keep the bag stocked with STORY_SMART_POTIONS of the potion a player would have by then (STORY_SMART), in
        the medicine pocket of the bag the game itself uses (find_bag), never anywhere else: a potion slot is set
        to that, or with none, the first empty slot. Test harness only, like the heal before a boss. Returns the
        number of potions in stock, 0 if the bag isn't known."""
        bag = self.bag
        if not bag:
            return 0
        mem, items = self.game.emu.memory.unsigned, self.data["items"]
        potions = {items[k] for k in ("POTION", "SUPER_POTION", "HYPER_POTION")}
        kind = items[self._potion_kind()]
        slots = [bag + BAG_MEDICINE + 4 * k for k in range(BAG_MEDICINE_SLOTS)]
        read = lambda a: (mem[a] | mem[a + 1] << 8, mem[a + 2] | mem[a + 3] << 8)
        target = next((a for a in slots if read(a)[0] in potions), None) or \
            next((a for a in slots if read(a) == (0, 0)), None)
        if target is None:
            return 0
        for k, b in enumerate(struct.pack("<HH", kind, SMART_POTIONS)):
            mem[target + k] = b
        return SMART_POTIONS

    def _potion_kind(self):
        """What a player would have bought by the party's level: Potions, Super Potions from Goldenrod, then Hyper."""
        level = max([m.level for m in self.party_mons() if m.valid()] or [1])
        return "POTION" if level < 15 else "SUPER_POTION" if level < 35 else "HYPER_POTION"

    def smart_mon(self, b):
        """Battler b's Pokemon as smart.py wants it, from the battle's own data."""
        import smart
        g, mem, bt = self.game, self.game.emu.memory.unsigned, self.data["boss_teams"]
        at = g.word(self.bsys + BATTLE_CONTEXT) + BATTLE_MONS + BATTLE_MON_SIZE * b
        u16 = lambda o: mem[at + o] | mem[at + o + 1] << 8
        moves = [self.move_names.get(u16(0x0C + 2 * k)) for k in range(4)]
        return dict(key=u16(0), name=self.species_names.get(u16(0), u16(0)),
                    types=[smart.TYPES[mem[at + BATTLE_MON_TYPES + k]] for k in range(2)
                           if mem[at + BATTLE_MON_TYPES + k] < len(smart.TYPES)],
                    moves=[bt.MOVES[m]["type"] for m in moves if m and bt.MOVES.get(m, {}).get("power")],
                    hp=u16(BATTLE_MON_HP), max_hp=u16(BATTLE_MON_MAX_HP))

    def smart_bench(self, active):
        """The party in the order the battle's party screen shows it, slot 0 being the Pokemon out: [dict(slot,
        name, types, moves, hp, max_hp)]. The order starts as the party's and follows each switch and replacement
        (smart_order); HP comes from the party, which the battle keeps up to date."""
        bt, names = self.data["boss_teams"], self.species_names
        # every slot, so that slot numbers stay those of the party screen; one that doesn't read (scrambled) or is
        # an egg can't come in, and counts as fainted below
        mons = self.party_mons()
        if not getattr(self, "smart_order", None) or len(self.smart_order) != len(mons):
            self.smart_order = list(range(len(mons)))
        if active is not None and mons[self.smart_order[0]].species != active:
            # slot 0 is the Pokemon out: a switch that did not go through leaves the order as it was
            k = next((k for k, i in enumerate(self.smart_order) if mons[i].species == active), None)
            if k is not None:
                self.smart_send(k)
        # the party above is the save's, whose HP the battle leaves alone until it ends; so HP is tracked here:
        # what each Pokemon had when last seen out (smart_hp), and 0 once it fainted. Nothing heals the bench
        seen = getattr(self, "smart_hp", {})
        hp_now = lambda m: seen.get(self.species_names.get(m.species), struct.unpack_from("<HH", m.stats, 6)[0])
        out = []
        for slot, i in enumerate(self.smart_order):
            m = mons[i]
            if not m.valid() or m.is_egg:
                out.append(dict(slot=slot, name=None, types=[], moves=[], hp=0, max_hp=1))
                continue
            hp, top = hp_now(m), struct.unpack_from("<HH", m.stats, 6)[1]
            moves = [self.move_names.get(m.u16(0x20 + 2 * k)) for k in range(4)]
            out.append(dict(slot=slot, name=names.get(m.species), types=bt.SPECIES.get(names.get(m.species), {}).get("types", []),
                            moves=[bt.MOVES[x]["type"] for x in moves if x and bt.MOVES.get(x, {}).get("power")],
                            hp=hp, max_hp=top))
        return out

    def smart_party(self, image):
        """A party screen after a faint (STORY_SMART): on the list, send in the best against the foe of those still
        standing (by the HP the bot has tracked); on the Shift screen that follows, shift. Returns frames used."""
        import smart
        g = self.game
        green = lambda xy: (lambda c: c[1] > 130 and c[0] < 120 and c[2] < 150)(image.getpixel(xy)[:3])
        if green((128, 215)) and green((128, 250)):          # the Shift screen: one wide green button
            if self.smart_party_slot is not None and not self.smart_party_fresh:
                g.touch(128, 100, after=90)
            else:
                g.key("b", after=40)                        # not one the bot chose: back to the list
            return 90
        if self.smart_party_fresh:
            party = self.smart_bench(self.smart_mon(0)["key"])     # the one that fainted is still in slot 0
            alive = [b for b in party[1:] if b["hp"] > 0]
            if not alive:
                g.key("b", after=40)
                return 40
            best = alive[smart.pick(self.smart_mon(1), alive)]
            self.smart_send(best["slot"])
            self.smart_party_fresh, self.smart_party_slot = False, best["slot"]
            print("  in: %s" % best["name"], flush=True)
        g.touch(*battle_test.PARTY_SLOTS[self.smart_party_slot], after=60)
        return 60

    def smart_send(self, slot):
        """slot comes in (on the party screen): note the new order."""
        o = self.smart_order
        o[0], o[slot] = o[slot], o[0]

    def smart_turn(self, image, n):
        """The player's command menu is up (STORY_SMART): fight, switch or heal, by smart.choose. On Fight the AI
        picks the move; a switch and a heal (a Hyper Potion from the bag) the bot does through the menus."""
        import smart
        g = self.game
        if not self.smart_fresh:                # the same turn's menu, not gone yet
            if self.smart_last == "fight":
                g.touch(128, 73, after=60)
            else:
                g.key("b", after=30)            # a switch or heal that did not go through: back to the menu
                self.smart_fresh = True
            return 60
        self.smart_fresh = False
        if "stocked" not in self.smart_state:
            self.smart_state["stocked"] = bool(self.bag)   # the field restock filled the bag before the battle
        me, foe = self.smart_mon(0), self.smart_mon(1)
        self.smart_hp[me["name"]] = me["hp"]
        party = self.smart_bench(me["key"])
        bench = [b for b in party[1:] if b["hp"] > 0]
        self.smart_state["items"] = SMART_POTIONS - sum(self.smart_state.get("heals", {}).values()) \
            if self.smart_state["stocked"] else 0             # no potion found to stock: no heals
        choice = smart.choose(me, foe, bench, self.smart_state)
        if os.environ.get("STORY_SMART_DEBUG"):
            print("  [turn: me %s %d/%d, order %s, party %s]" % (me["name"], me["hp"], me["max_hp"], self.smart_order,
                  [(b["name"], b["hp"]) for b in party]), flush=True)
        self.choices.append(choice)
        self.smart_last = choice
        if choice == "fight":
            g.touch(128, 73, after=60)
            return 60
        if choice == "heal":
            print("  heal: a potion on %s (%d/%d HP) against %s" % (me["name"], me["hp"], me["max_hp"], foe["name"]),
                  flush=True)
            def until(test, frames):            # wait for a screen, up to so many frames
                for _ in range(frames // 20):
                    if test(g.emu.screenshot()):
                        return True
                    g.run(20)
                return False
            party_up = lambda im: battle_test.screen_state(im) == "party"
            for xy, wait in (((36, 172), 200), ((64, 50), 150), ((64, 40), 200), ((110, 172), 60)):
                g.touch(*xy, after=wait)
            until(party_up, 400)
            for _ in range(3):                  # "Use on which Pokemon?": the one out, in the first slot
                g.touch(*battle_test.PARTY_SLOTS[0], after=120)
                if not until(party_up, 60):
                    break
            return 800
        target = bench[smart.pick(foe, bench)]
        print("  switch: %s (%d/%d HP) out for %s against %s" % (me["name"], me["hp"], me["max_hp"], target["name"],
                                                                  foe["name"]), flush=True)
        for xy, wait in (((220, 172), 200), (battle_test.PARTY_SLOTS[target["slot"]], 120), ((128, 100), 90)):
            g.touch(*xy, after=wait)
        # should the Shift screen still show, the party screen code shifts this one
        self.smart_party_fresh, self.smart_party_slot = False, target["slot"]

        self.smart_send(target["slot"])
        return 410

    def battle(self):
        """Fight until the battle ends. The game's own trainer AI picks the player's moves and replacements
        (see hand_to_ai); the bot only moves the text on. Should a menu still show, it falls back to the first
        move and the next healthy Pokemon."""
        g = self.game
        ai = False
        start, moves = self.last_place, self.ai_moves
        if start and start[0] == "T10R0701":    # the Hall of Fame scene draws like a battle screen; it is none
            return
        print("  battle by %s" % (start,), flush=True)
        for i in range(600):
            if self.hand_to_ai():
                ai = True
                break
            g.run(1)
        toggle, frames, menus = 0, 0, 0
        white = 0
        # the player's money, at the address it has now: a scripted battle (Lyra's catching lesson) reads
        # another trainer's profile, and the game's latest profile is then not the player's
        money_at = g.profile + 20 if g.profile else None
        cash = lambda: g.word(money_at) if money_at else None
        money = cash()
        mons = {}
        first_ko, began = len(self.kos), g.frames
        self.first_ko = first_ko
        self.switches, self.choices, self.smart_state = [], [], {}
        self.smart_fresh, self.smart_last, self.smart_order = True, None, None
        self.smart_party_fresh, self.smart_party_slot, self.smart_hp = True, None, {}
        items_left, items_most, self.items_used = None, 0, 0
        # who the opponents are, read now: the battle's memory is gone once it ends
        self.trainer_ids = []
        if self.bsys:
            mem = g.emu.memory.unsigned
            self.trainer_ids = [mem[self.bsys + BATTLE_TRAINER_IDS + 2 * b] | mem[self.bsys + BATTLE_TRAINER_IDS + 2 * b + 1] << 8
                                for b in (1, 3)]
        while not g.in_field() and frames < 60 * 60 * 20:
            mons = self.watch_kos(start, mons)
            if BATTLE_ITEMS and self.bsys:          # how many of the player's items are left, while the battle lasts
                at = self.bsys + BATTLE_TRAINERS + TRAINER_ITEMS
                left = sum(1 for k in range(4) if g.emu.memory.unsigned[at + 2 * k] | g.emu.memory.unsigned[at + 2 * k + 1] << 8)
                if items_left is None or left != items_left:
                    print("  player's items: %s" % [g.emu.memory.unsigned[at + 2 * k] | g.emu.memory.unsigned[at + 2 * k + 1] << 8
                                                    for k in range(4)], flush=True)
                if items_left is not None and left < items_left:
                    print("  item used: %d left" % left, flush=True)
                items_left = left
                items_most = max(items_most, left)         # once the slots are filled
                self.items_used = items_most - left
            # losing costs half the player's money, and nothing else in a battle takes money away
            now = cash()
            if money and now is not None and now < money:
                self.record_battle(start, "lost", g.frames - began, self.ai_moves - moves, self.kos[first_ko:])
                self.battling = False
                self.stuck("lost a battle by %s: the team whited out (money %d -> %d)" % (start, money, now))
            image = g.emu.screenshot()
            # a battle lost fades both screens to white before the player wakes at a Pokemon Center
            if all(min(image.getpixel(p)[:3]) > 235 for p in ((20, 20), (128, 96), (236, 170), (128, 300))):
                white += 1
                if white > 30:
                    self.stuck("lost a battle: the team whited out")
            else:
                white = 0
            # after a loss the player wakes at a Pokemon Center: on a map again, but not the one the battle began
            # on; and on the way there every Pokemon of the party has no HP left
            here = self.where()
            # (a change between two outdoor maps is no whiteout: those wake the player indoors, at a Pokemon
            # Center; and the map read at the start can lag a step behind, on the edge of two routes)
            if here and start and here[0] != start[0] and not self.same_region(here[0], start[0]):
                self.record_battle(start, "lost", g.frames - began, self.ai_moves - moves, self.kos[first_ko:])
                self.battling = False
                self.stuck("lost a battle by %s: the team whited out" % (start,))
            if toggle % 5 == 0 and self.party_fainted():
                self.record_battle(start, "lost", g.frames - began, self.ai_moves - moves, self.kos[first_ko:])
                self.battling = False
                self.stuck("lost a battle by %s: every Pokemon fainted" % (start,))
            state = battle_test.screen_state(image)
            if SMART and state == "other" and all(max(image.getpixel(p)[:3]) < 90 for p in ((36, 364), (220, 364))) \
                    and image.getpixel((128, 247))[:3] == (248, 168, 176):
                state = "menu"      # the command menu with its cursor showing: Fight pink, the labels dark
            if state != "menu":
                self.smart_fresh = True            # the next command menu is a new turn
            if state not in ("party", "confirm"):
                self.smart_party_fresh = True      # and the next party screen a new choice
            if state in ("menu", "moves", "party"):
                menus += 1
            if state == "menu" and SMART:
                frames += self.smart_turn(image, menus)
            elif state == "menu":
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
                if SMART:
                    frames += self.smart_party(image)
                    continue
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
                # B moves the text on as A does, but does nothing on the command menu, which the bot must see
                # before anything picks Fight on it (STORY_SMART)
                bottom = image.getpixel((128, 247))[:3]
                # the move-to-forget list and the move's page share a purple band across the top of the screen
                forget = all(image.getpixel(xy)[:3] == (168, 104, 240) for xy in ((8, 206), (240, 206)))
                if SMART and forget:
                    g.touch(238, 172, after=60)     # "which move should be forgotten?": back, to keep the set
                elif SMART and bottom not in ((248, 168, 176), (232, 56, 56)):
                    g.key("a", after=30)            # not the battle menu's screen (learning a move, yes or no)
                else:
                    g.key("b" if SMART or not toggle % 3 else "a", after=30)
                frames += 36
        here = self.where()
        if money and cash() is not None and cash() < money or (here and start and here[0] != start[0]
                                                               and not self.same_region(here[0], start[0])):
            self.record_battle(start, "lost", g.frames - began, self.ai_moves - moves, self.kos[first_ko:])
            self.battling = False
            self.stuck("lost a battle by %s: the team whited out" % (start,))
        if not g.in_field():
            self.stuck("a battle did not end")
        self.battling = False
        if SMART and self.find_bag():
            self.restock_field()                # the potions used, back in the bag before the next battle
        self.record_battle(start, "won", g.frames - began, self.ai_moves - moves, self.kos[first_ko:])
        self.log.append(dict(at=self.where(), ai=ai, menus=menus))
        print("  battle over: %d AI moves, %d menus, now at %s" % (self.ai_moves - moves, menus, self.where()), flush=True)

    # ------------------------------------------------------------- the team

    def party(self):
        """Address of the party in RAM: {max 6, count, six 236-byte Pokemon}, found by its first valid Pokemon."""
        g = self.game
        def ok(at):
            count = g.word(at) == 6 and g.word(at + 4)
            if not count or count > 6:
                return False
            # any Pokemon will do: the game may be part way through rewriting one
            for i in range(count):
                mon = pkm.Mon(bytes(g.emu.memory.unsigned[at + 8 + pkm.PARTY_SIZE * i:at + 8 + pkm.PARTY_SIZE * (i + 1)]))
                if mon.valid() and mon.species and 0 < mon.level <= 100:
                    return True
            return False
        if self.party_at and ok(self.party_at):
            return self.party_at
        ram = bytes(g.emu.memory.unsigned[0x02000000:0x02400000])
        at = ram.find(struct.pack("<I", 6))
        while at >= 0:
            if at % 4 == 0 and ok(0x02000000 + at):
                self.party_at = 0x02000000 + at
                return self.party_at
            at = ram.find(struct.pack("<I", 6), at + 1)
        self.stuck("could not find the party in memory")

    def party_mons(self):
        at = self.party()
        mem = self.game.emu.memory.unsigned
        return [pkm.Mon(bytes(mem[at + 8 + pkm.PARTY_SIZE * i:at + 8 + pkm.PARTY_SIZE * (i + 1)]))
                for i in range(self.game.word(at + 4))]

    def party_healthy(self):
        """Whether every Pokemon of the party (not counting eggs) has all its HP."""
        mons = [m for m in self.party_mons() if m.valid() and not m.is_egg]
        return bool(mons) and all(struct.unpack_from("<HH", m.stats, 6)[0] == struct.unpack_from("<HH", m.stats, 6)[1]
                                  for m in mons)

    def party_fainted(self):
        """Whether every Pokemon of the party (not counting eggs) has no HP left."""
        try:
            mons = [m for m in self.party_mons() if m.valid() and not m.is_egg]
        except Stuck:
            return False
        return bool(mons) and all(struct.unpack_from("<H", m.stats, 6)[0] == 0 for m in mons)

    def swap_team(self, name, level=None):
        """At a Pokemon Center: box the party and take out the boss's set (team_sets.py), healthy."""
        spec = team_sets.SETS[name]
        # STORY_LEVEL_<SET>=N: the set at another level, as a player would have it then (LEVEL_CURVE.md)
        level = level or os.environ.get("STORY_LEVEL_" + name.upper())
        if level:
            spec = self.sets.at_level(spec, int(level))
        at = self.party()
        mons = self.party_mons()
        template = next(m for m in mons if m.valid() and not m.is_egg)
        built = [self.sets.build(template, species, spec) for species in spec["team"]]
        if not self.write_party([mon for mon, _, _ in built]):
            self.stuck("the %s set did not go into the party" % name)
        self.team = name
        print("  team: %s set, %s" % (name, ", ".join("%s Lv. %d" % (s, spec["level"]) for s in spec["team"])),
              flush=True)

    def write_party(self, mons):
        """Put these Pokemon in the party, in RAM. The game keeps decrypting the lead in place for a few frames
        at a time (the walking Pokemon reads it) and encrypts it again after; data written in that window comes
        out scrambled. So write when the lead reads whole, and check over the next frames that it stays the
        Pokemon written."""
        at = self.party()
        data = b"".join(mon.encode() for mon in mons) + bytes(pkm.PARTY_SIZE * (6 - len(mons)))
        mem = self.game.emu.memory.unsigned
        g = self.game
        lead = lambda: pkm.Mon(bytes(mem[at + 8:at + 8 + pkm.PARTY_SIZE]))
        # the Pokemon walking behind the player (the first that hasn't fainted, not always the lead) is the one
        # the game decrypts in place: write only at a moment when every one reads whole
        whole = lambda: all(m.valid() for m in self.party_mons())
        for attempt in range(10):
            for _ in range(120):
                if whole():
                    break
                g.run_every_frame(1)
            for i, b in enumerate(struct.pack("<I", len(mons)) + data):
                mem[at + 4 + i] = b
            # a write that landed while the game had the walking Pokemon decrypted is scrambled when the game
            # encrypts it again, a few frames on
            # each slot, judged on its own: it must read as the Pokemon written at least once over the 60 frames
            # after the write (the walking one reads only between the game's decryptions), and never read as
            # anything else; a scrambled slot never reads again
            want = [m.species for m in mons]
            good, bad = [False] * len(want), False
            for _ in range(60):
                g.run_every_frame(1)
                for k, m in enumerate(self.party_mons()[:len(want)]):
                    if m.valid():
                        good[k] = good[k] or m.species == want[k]
                        bad = bad or m.species != want[k]
            if all(good) and not bad:
                return True
        return False

    def restore_party(self, why, refill=False, lead=None):
        """TEST HARNESS ONLY: heal the party where it stands (all HP, no status, all PP), in place of the
        potions a player would use. The bot can't use items, so a boss behind a gym full of trainers would
        otherwise be fought with whatever the trainers left. With refill, a berry used up is given back too
        (the team set's item for that Pokemon), as a player carrying several would."""
        names = {v: k for k, v in self.sets.move_ids.items()}
        species = {v: k for k, v in self.sets.species_ids.items()}
        held = team_sets.SETS.get(self.team, {}).get("items", {}) if refill and self.team else {}
        mons = []
        # read the party at a moment when every Pokemon reads whole (see write_party): one read half way
        # through the game's own rewriting would be written back as garbage
        for _ in range(240):
            party = self.party_mons()
            if all(m.valid() for m in party):
                break
            self.game.run_every_frame(1)
        else:
            self.stuck("the party never read whole (%s)" % why)
        for m in party:
            if m.valid() and not m.is_egg:
                item = held.get(species.get(m.species))
                if item and not m.u16(0x02):
                    m.set_u16(0x02, self.sets.item_ids[item])
                struct.pack_into("<I", m.stats, 0, 0)                          # status
                struct.pack_into("<H", m.stats, 6, struct.unpack_from("<H", m.stats, 8)[0])   # HP
                for i in range(4):
                    move = m.u16(0x20 + 2 * i)
                    if move:
                        m.blocks[0x28 + i] = self.sets.pp.get(names.get(move), m.blocks[0x28 + i])
            mons.append(m)
        if lead:
            # a player puts the Pokemon they want out first at the front of the party between battles; a list
            # gives the front of the party in order
            order = [lead] if isinstance(lead, str) else list(lead)
            first = [m for name in order for m in mons if species.get(m.species) == name]
            mons = first + [m for m in mons if m not in first]
        if not self.write_party(mons):
            # once, after two losses to Lance, the start menu was open and the write never checked out: close
            # whatever is open and try once more
            for _ in range(3):
                self.game.key("b", after=20)
            self.settle()
            if not self.write_party(mons):
                self.stuck("could not heal the party (%s)" % why)
        print("  heal: party restored in place (%s), standing in for potions" % why, flush=True)

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
        bot.game.run(60 + (random.randint(0, JITTER) if JITTER else 0))
    results = []
    json.dump(results, open(os.path.join(out, "story.json"), "w"))
    for stage in stages[begin:end]:
        frames = bot.game.frames
        battles, ai_moves = len(bot.log), bot.ai_moves
        bot.shut = set()        # doors open as the story goes on
        # STORY_SWAP_<STAGE>=set:level: before the stage, the party becomes that set at that level, standing in
        # for a short grind a player would do (the sets otherwise change only at the heals that swap them)
        if SMART and bot.has_pokemon() and bot.find_bag():
            bot.restock_field()     # (with a Pokemon in the party, the menu has its Bag)
        swap = os.environ.get("STORY_SWAP_" + stage.__name__.upper())
        if swap:
            name, _, level = swap.partition(":")
            bot.swap_team(name, int(level) if level else None)
        before = os.path.join(out, "before_%s.dst" % stage.__name__)
        bot.save(before)
        losses = 0
        try:
            while True:
                try:
                    stage(bot)
                    break
                except Stuck as e:
                    # a player who loses tries again: back to the start of the stage, up to RETRIES times
                    if not str(e).startswith("lost a battle") or losses >= RETRIES:
                        raise
                    losses += 1
                    print("%-24s lost   %s; trying again (%d)" % (stage.__name__, e, losses), flush=True)
                    bot.game.emu.savestate.load_file(before)
                    bot.game.run(60 + (random.randint(0, JITTER) if JITTER else 0))
                    bot.battling = False
                    bot.shut = set()        # doors the first try found shut may be open from the stage's start
        except Stuck as e:
            results.append(dict(stage=stage.__name__, result="stuck", note=str(e)))
            json.dump(results, open(os.path.join(out, "story.json"), "w"), indent=1)
            print("%-24s STUCK  %s" % (stage.__name__, e), flush=True)
            break
        bot.save(os.path.join(out, "stage_%s.dst" % stage.__name__))
        minutes = (bot.game.frames - frames) / 3600
        results.append(dict(stage=stage.__name__, result="ok", at=bot.where(), losses=losses, game_minutes=round(minutes, 1),
                            battles=len(bot.log) - battles, ai_moves=bot.ai_moves - ai_moves,
                            menu_screens=sum(b["menus"] for b in bot.log[battles:])))
        json.dump(results, open(os.path.join(out, "story.json"), "w"), indent=1)
        print("%-24s ok     at %-28s %5.1f game minutes, %d battles, %d AI moves" % (
            stage.__name__, bot.where(), minutes, len(bot.log) - battles, bot.ai_moves - ai_moves), flush=True)
    json.dump(results, open(os.path.join(out, "story.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
