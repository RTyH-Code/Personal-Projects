#!/usr/bin/env python3
"""Overworld playtester for HeartGold QoL + Hard.

    walk_test.py TEST_ROM TREE DUMP OUT [sweep] [legendaries] [wild] [features] [--jobs N] [--maps CODE,CODE]

TEST_ROM is a build of the hack with the harness from make_harness.py, TREE
the hg-engine tree it was built from and DUMP a vanilla `make dump_scripts`
tree (for the maps' events). It needs py-desmume and ndspy.

Every test starts from a save state in the player's bedroom, has the harness
give a level 100 party, badges and items and warp the player, and then
drives the game with the buttons while reading the player's map and position
from memory.

    sweep        warp to every map and check that it loads and that the
                 player can take a step ("scene" means a trainer or a story
                 scene started first, which also shows the map works)
    legendaries  go to each legendary the hack adds: with its story gate
                 closed it must not be there, with it open talking to it must
                 start a battle with the right Pokemon at the right level
    wild         walk in the grass or cave of every map that has wild
                 Pokemon until a few appear, and check each against the
                 hack's encounter tables

    features     use the fossil reviver, buy from the evolution item shop
                 with no badges and with all of them, and use Surf from
                 the bag

With no test named, all four run. Results go to OUT/walk_results.json and a
summary is printed; problems get a screenshot in OUT.
"""
import glob
import json
import os
import re
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import battle_test

PLAYER_AVATAR_GET_X = 0x0205C67C   # PlayerAvatar_GetXCoord(avatar)
POKE_PARA_SET = 0x0206DE38         # PokeParaSet(mon, species, level, ...): every Pokemon the game creates
BAG_ADD_ITEM = 0x02078398          # Bag_AddItem(bag, item, quantity, heap)
FLAGS_OFFSET = 0x2E0               # the flags, after the variables in the same block
DIRS = {"up": (0, -1, 0), "down": (0, 1, 1), "left": (-1, 0, 2), "right": (1, 0, 3)}
WATER = (0x10, 0x15)
GRASS = (0x02, 0x03)
CAVE_FLOOR = (0x08,)
ENCOUNTERS_WANTED = 3
STEPS_PER_ENCOUNTER = 250


# ------------------------------------------------------------------ data

class World:
    """Maps, their collision and their events, from the ROM and the two trees."""

    def __init__(self, rom_path, tree, dump):
        import ndspy.narc
        import ndspy.rom
        self.tree, self.dump = tree, dump
        rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
        self.matrices = ndspy.narc.NARC(rom.getFileByName("a/0/4/1")).files
        self.lands = ndspy.narc.NARC(rom.getFileByName("a/0/6/5")).files
        read = lambda p: open(os.path.join(tree, p)).read()
        self.map_ids = {n: int(v) for n, v in re.findall(r"^\.equ MAP_(\w+), (\d+)", read("asm/include/maps.inc"), re.M)}
        self.map_names = {v: n for n, v in self.map_ids.items()}
        self.flags = {n: int(v, 0) for n, v in re.findall(r"^\.equ (FLAG_\w+), (\w+)", read("asm/include/flags.inc"), re.M)}
        self.vars = {n: int(v, 0) for n, v in re.findall(r"^\.equ (VAR_\w+), (\w+)", read("asm/include/vars.inc"), re.M)}
        arm9 = b"".join(s.data for s in rom.loadArm9().sections)
        # the map header table: 24 bytes a map. New Bark Town's header has matrix 0, scripts 842 and init
        # scripts 615, which finds the table.
        at = arm9.index(struct.pack("<HHH", 0, 842, 615)) - 4 - 24 * self.map_ids["T20"]
        self.headers = {}
        for name, i in self.map_ids.items():
            h = arm9[at + 24 * i:at + 24 * i + 24]
            self.headers[name] = dict(encounters=h[0], matrix=struct.unpack_from("<H", h, 4)[0],
                                      events=struct.unpack_from("<H", h, 16)[0])
        self.grids, self.owners = {}, {}
        self.encounters = self.load_encounters(read("data/Encounters.c"))

    @staticmethod
    def load_encounters(text):
        tables = []
        for m in re.finditer(r"^    \[ENCDATA_(\w+)\] = \{\n(.*?)^    \},\n", text, re.S | re.M):
            body = m.group(2)
            levels = [int(x) for x in re.search(r"\.levels = \{(.*?)\}", body, re.S).group(1).replace("\n", " ").split(",") if x.strip()]
            land = {}
            for part in ("Morning", "Day", "Night"):
                names = re.findall(r"SPECIES_(\w+)", re.search(r"\.species%s = \{(.*?)\}" % part, body, re.S).group(1))
                for level, name in zip(levels, names):
                    land.setdefault(name, set()).add(level)
            extra = set()
            for key in ("hoennSoundSpecies", "sinnohSoundSpecies"):
                extra.update(re.findall(r"SPECIES_(\w+)", re.search(r"\.%s = \{(.*?)\}" % key, body, re.S).group(1)))
            extra.update(re.findall(r"\.landSwarm = SPECIES_(\w+)", body))
            tables.append(dict(name=m.group(1), rate=int(re.search(r"\.rateWalk = (\d+)", body).group(1)),
                               land=land, extra=extra - {"NONE"}, levels=set(levels)))
        return tables

    def grid(self, matrix):
        """Tile permissions of a whole map matrix, and for each tile the map it belongs to (if the matrix says)."""
        if matrix not in self.grids:
            d = self.matrices[matrix]
            w, h, has_headers, has_heights, name_length = d[0], d[1], d[2], d[3], d[4]
            o = 5 + name_length
            owners = None
            if has_headers:
                owners = struct.unpack_from("<%dH" % (w * h), d, o)
                o += 2 * w * h
            if has_heights:
                o += w * h
            lands = struct.unpack_from("<%dH" % (w * h), d, o)
            grid, owner = {}, {}
            for i, land in enumerate(lands):
                if land == 0xFFFF:
                    continue
                data = self.lands[land]
                off = 16
                if struct.unpack_from("<H", data, off)[0] == 0x1234:   # a background-sound block comes first
                    off += 4 + struct.unpack_from("<H", data, off + 2)[0]
                tiles = struct.unpack_from("<1024H", data, off)
                for t, v in enumerate(tiles):
                    p = ((i % w) * 32 + t % 32, (i // w) * 32 + t // 32)
                    grid[p] = v
                    if owners:
                        owner[p] = owners[i]
            self.grids[matrix], self.owners[matrix] = grid, owner
        return self.grids[matrix], self.owners[matrix]

    def events(self, name):
        """A map's events: the hack's own file when it has one, else the original."""
        number = self.headers[name]["events"]
        for base in (self.tree, self.dump):
            found = glob.glob(os.path.join(base, "data/eventdata/zone_event/%03d_*.json" % number))
            if found:
                return json.load(open(found[0]))
        return dict(object_events=[], warp_events=[], bg_events=[], coord_events=[])

    def tiles(self, name):
        """The tiles of a map that can be stood on: {(x, z): behaviour}, and the tiles its events occupy."""
        grid, owner = self.grid(self.headers[name]["matrix"])
        mine = self.map_ids[name]
        events = self.events(name)
        occupied = {(e["x"], e["z"]) for k in ("object_events", "warp_events", "bg_events", "coord_events")
                    for e in events.get(k, [])}
        open_tiles = {p: v & 0xFF for p, v in grid.items() if not v & 0x8000 and (not owner or owner[p] == mine)}
        if not open_tiles:      # a map that borrows another map's matrix
            open_tiles = {p: v & 0xFF for p, v in grid.items() if not v & 0x8000}
        return open_tiles, occupied, events

    def landing(self, name, want=None):
        """A tile to warp to: open, on plain ground (or of the wanted kind), with room to step, near the map's
        own events so that it is somewhere a player can really get to."""
        tiles, occupied, events = self.tiles(name)
        if not tiles:
            return None
        wanted = (lambda b: b in want) if want else (lambda b: b not in WATER)
        anchors = [(e["x"], e["z"]) for k in ("warp_events", "object_events", "bg_events") for e in events.get(k, [])]
        anchors = [a for a in anchors if any((a[0] + dx, a[1] + dz) in tiles for dx in (-2, -1, 0, 1, 2) for dz in (-2, -1, 0, 1, 2))]
        best = None
        for p, b in tiles.items():
            if p in occupied or not wanted(b):
                continue
            free = [d for d, (dx, dz, _) in DIRS.items()
                    if (p[0] + dx, p[1] + dz) in tiles and (p[0] + dx, p[1] + dz) not in occupied
                    and wanted(tiles[(p[0] + dx, p[1] + dz)])]
            if not free:
                continue
            near_event = any(abs(p[0] - x) + abs(p[1] - z) <= 1 for x, z in occupied)
            distance = min((abs(p[0] - x) + abs(p[1] - z) for x, z in anchors), default=0)
            score = (near_event, abs(distance - 3) if anchors else 0, -len(free), p[1], p[0])
            if best is None or score < best[0]:
                best = (score, p, free)
        return best and (best[1], best[2])


# -------------------------------------------------------------- emulator

def text_box(image):
    """Whether a message box is open at the bottom of the top screen: a wide, mostly white band."""
    band = image.crop((12, 152, 236, 186)).convert("L")
    white = sum(1 for v in band.getdata() if v > 225)
    return white > 0.6 * band.size[0] * band.size[1]


class Walker(battle_test.Game):
    def __init__(self, rom):
        super().__init__(rom)
        from desmume.controls import Keys, keymask
        for n, k in (("down", Keys.KEY_DOWN), ("left", Keys.KEY_LEFT), ("right", Keys.KEY_RIGHT), ("x", Keys.KEY_X)):
            self.keys[n] = keymask(k)
        self.avatar = None
        self.avatar_calls = 0
        self.created = []
        self.emu.memory.register_exec(PLAYER_AVATAR_GET_X, self._avatar)
        self.emu.memory.register_exec(POKE_PARA_SET, self._created)
        self.added = []
        self.emu.memory.register_exec(BAG_ADD_ITEM, self._added)

    def _avatar(self, address, size):
        self.avatar = self.emu.memory.register_arm9.r0 & 0xFFFFFFFF
        self.avatar_calls += 1

    def _created(self, address, size):
        r = self.emu.memory.register_arm9
        self.created.append((r.r1 & 0xFFFF, r.r2 & 0xFF))

    def _added(self, address, size):
        r = self.emu.memory.register_arm9
        self.added.append((r.r1 & 0xFFFF, r.r2 & 0xFFFF))

    def word(self, address):
        m = self.emu.memory.unsigned
        return m[address] | m[address + 1] << 8 | m[address + 2] << 16 | m[address + 3] << 24

    def position(self):
        """(object's map field, x, z, facing) of the player, or None when there is no player on a map."""
        if not self.avatar or not 0x02000000 <= self.avatar < 0x02400000:
            return None
        obj = self.word(self.avatar + 0x30)
        if not 0x02000000 <= obj < 0x02400000:
            return None
        return self.word(obj + 0x0C), self.word(obj + 0x64), self.word(obj + 0x6C), self.word(obj + 0x28)

    def set_flag(self, flag, on=True):
        a = self.vars_pointer + FLAGS_OFFSET + flag // 8
        m = self.emu.memory.unsigned
        m[a] = (m[a] | 1 << flag % 8) if on else (m[a] & ~(1 << flag % 8))

    def in_field(self):
        """Whether the overworld is running (the game asks for the player's position every frame there)."""
        before = self.avatar_calls
        self.run(20)
        return self.avatar_calls > before

    def black(self):
        image = self.emu.screenshot().crop((0, 0, 256, 192)).convert("L")
        return image.getextrema()[1] < 16

    def start(self, state_path, data, world, name, tile, facing=1, flags=(), variables=(), items=(), party=None,
              badges=16):
        """Load the bedroom state and have the harness warp the player. Returns the position reached or None."""
        self.emu.savestate.load_file(state_path)
        self.vars_pointer = None
        self.avatar = None
        self.frames = 0
        self.run(40)
        if self.vars_pointer is None:
            return None
        reference = battle_test.reference_party(data, 100)
        for i, (_, species_id, _, moves, item) in enumerate(reference):
            self.set_var(0x4000 + i, (party[i] if party and i < len(party) else species_id))
            self.set_var(0x4006 + i, 100)
            self.set_var(0x4010 + i, item)
            for j in range(4):
                self.set_var(0x4020 + 4 * i + j, moves[j] if j < len(moves) else 0)
        for i in range(4):
            self.set_var(0x4038 + i, items[i] if i < len(items) else 0)
        self.set_var(0x400E, 1)
        self.set_var(0x400D, badges)
        self.set_var(0x403C, world.map_ids[name])
        self.set_var(0x403D, tile[0])
        self.set_var(0x403E, tile[1])
        self.set_var(0x403F, facing)
        for flag in flags:
            self.set_flag(world.flags[flag])
        for var, value in variables:
            self.set_var(world.vars[var], value)
        self.key("a")
        for _ in range(60):
            self.run(20)
            p = self.position()
            # the bedroom is a few tiles across, so being on the target tile means the warp happened
            if p and p[1:3] == tuple(tile) and not self.black() and self.in_field():
                self.run(180)       # the harness script is still fading the screen in
                self.created = []
                return self.position()
        return None

    def step(self, direction, frames=18):
        """Hold a direction for about one tile and return the new position."""
        self.key(direction, hold=frames, after=6)
        return self.position()

    def text_box(self):
        """Whether a message box is open at the bottom of the top screen."""
        return text_box(self.emu.screenshot())

    def shot(self, path):
        self.emu.screenshot().save(path)


# ----------------------------------------------------------------- tests

def sweep(game, state, data, world, names, out_dir, results):
    for name in names:
        r = dict(test="sweep", map=name)
        spot = world.landing(name)
        if not any(world.events(name).get(k) for k in ("warp_events", "object_events", "bg_events", "coord_events")):
            r.update(result="skipped", note="no events at all: not a map the player walks on")
        elif spot is None:
            r.update(result="skipped", note="no tile to stand on")
        else:
            tile, free = spot
            p = game.start(state, data, world, name, tile)
            if p is None and game.position() and not game.black() and (game.text_box() or game.in_field()):
                # the screen shows a map but the player is not where the warp put them
                r.update(result="scene", note="a story scene moved the player on arrival", tile=tile)
                game.shot(os.path.join(out_dir, "sweep_%s.png" % name))
            elif p is None:
                r.update(result="failed", note="the map did not load", tile=tile)
                game.shot(os.path.join(out_dir, "sweep_%s.png" % name))
            else:
                moved = False
                for direction in (free + [d for d in DIRS if d not in free]) * 3:
                    before = game.position()
                    after = game.step(direction, 24)
                    if after and before and after[1:3] != before[1:3]:
                        moved = True
                        break
                if moved:
                    r.update(result="ok", tile=tile)
                elif game.text_box():
                    # a trainer saw the player or a story scene began: the map works, the walk is over
                    r.update(result="scene", note="a trainer or a story scene took over", tile=tile)
                    game.shot(os.path.join(out_dir, "sweep_%s.png" % name))
                else:
                    r.update(result="stuck", note="the player could not take a step", tile=tile, at=p[1:3])
                    game.shot(os.path.join(out_dir, "sweep_%s.png" % name))
        results.append(r)
        print("sweep %-12s %-8s %s" % (name, r["result"], r.get("note", "")), flush=True)


def legendaries(game, state, data, world, names, out_dir, results):
    """Each legendary the hack adds, at its real place: absent with its gate closed, a battle with it open."""
    import legendaries as tool            # the hack's own list, from TREE/tools/hack
    species = data["species"]
    gate_flags = ["FLAG_GAME_CLEAR", "FLAG_UNLOCKED_MT_SILVER", "FLAG_CAUGHT_KYOGRE"]
    gate_vars = [("VAR_UNK_4131", 1)]
    regis = [species[n] for n in ("REGIROCK", "REGICE", "REGISTEEL")]
    for entry in tool.NEW:
        name, level, code, position, conditions = entry[0], entry[1], entry[2], tuple(entry[6]), entry[7]
        if code not in names:
            continue
        tiles, occupied, _ = world.tiles(code)
        sides = [(d, (position[0] - dx, position[1] - dz)) for d, (dx, dz, _) in DIRS.items()]
        sides = [(d, t) for d, t in sides if t in tiles and t not in occupied]
        if any(tiles[t] not in WATER for _, t in sides):    # one that stands on land is met from land
            sides = [(d, t) for d, t in sides if tiles[t] not in WATER]
        r = dict(test="legendaries", map=code, pokemon=name, level=level)
        if not sides:
            r.update(result="failed", note="no tile to stand on next to it")
        else:
            needs_regis = any("REGIROCK" in c for c in conditions)
            flags, variables = list(gate_flags), list(gate_vars)
            if name == "GROUDON":      # a save that has caught Kyogre also has these
                flags.append("FLAG_HIDE_EMBEDDED_TOWER_KYOGRE")
                variables.append(("VAR_SCENE_EMBEDDED_TOWER", 4))
            opened = dict(flags=flags, variables=variables, party=regis if needs_regis else None)
            closed = dict(flags=flags, variables=variables) if needs_regis else {}   # all but the three Regis
            notes, worked = [], []
            # closed from one side, then open from every side a player could stand on
            for gate_open, (direction, tile) in [(False, sides[0])] + [(True, side) for side in sides]:
                p = game.start(state, data, world, code, tile, facing=DIRS[direction][2],
                               **(opened if gate_open else closed))
                if p is None:
                    notes.append("the map did not load with the gate %s" % ("open" if gate_open else "closed"))
                    game.shot(os.path.join(out_dir, "legend_%s_%d.png" % (name, gate_open)))
                    continue
                game.key(direction, hold=2, after=10)     # make sure the player faces it
                game.created = []
                game.key("a")
                for _ in range(30):
                    game.run(20)
                    if game.created:
                        break
                met = (species[name], level) in game.created
                if gate_open and met:
                    worked.append(direction)
                if gate_open and not met:
                    notes.append("no battle when facing %s from %s (created: %s)" % (direction, tile, game.created[:3]))
                    game.shot(os.path.join(out_dir, "legend_%s_%s.png" % (name, direction)))
                if not gate_open and game.created:
                    notes.append("a battle with the gate closed (created: %s)" % game.created[:3])
                    game.shot(os.path.join(out_dir, "legend_%s_closed.png" % name))
            tile = sides[0][1]
            r["sides"] = worked
            r.update(result="failed" if notes else "ok", tile=tile, note="; ".join(notes))
        results.append(r)
        print("legendaries %-10s %-10s %-6s %s" % (code, name, r["result"], r.get("note", "")), flush=True)


def wild(game, state, data, world, names, out_dir, results):
    """Walk where wild Pokemon live until a few appear and check them against the hack's tables."""
    species_names = {v: k for k, v in data["species"].items()}
    for name in names:
        bank = world.headers[name]["encounters"]
        if bank >= len(world.encounters) or world.encounters[bank]["rate"] == 0:
            continue
        table = world.encounters[bank]
        tiles, _, _ = world.tiles(name)
        # outdoors they live in the grass; caves mark the floor they live on, where they mark anything
        kinds = set(tiles.values())
        want = GRASS if kinds & set(GRASS) else CAVE_FLOOR if kinds & set(CAVE_FLOOR) else None
        spot = world.landing(name, want=want)
        r = dict(test="wild", map=name, table=table["name"], seen=[])
        if spot is None:
            r.update(result="skipped", note="no tile to walk on")
        else:
            tile, free = spot
            p = game.start(state, data, world, name, tile)
            if p is None:
                r.update(result="failed", note="the map did not load")
            else:
                there = free[0]
                back = {"up": "down", "down": "up", "left": "right", "right": "left"}[there]
                wrong, steps, note, walked = [], 0, "", 0
                while len(r["seen"]) < ENCOUNTERS_WANTED and steps < STEPS_PER_ENCOUNTER * ENCOUNTERS_WANTED:
                    game.created = []
                    before = game.position()
                    after = game.step(there if steps % 2 == 0 else back)
                    walked += bool(before and after and before[1:3] != after[1:3])
                    steps += 1
                    if (steps == 12 and walked == 0) or (not game.created and game.text_box()):
                        note = "could not walk (a trainer or a story scene took over)"
                        game.shot(os.path.join(out_dir, "wild_%s.png" % name))
                        break
                    if not game.created:
                        continue
                    for _ in range(100):               # the battle's opening, up to the first menu
                        game.run(20)
                        if battle_test.screen_state(game.emu.screenshot()) == "menu":
                            break
                    met = [(species_names.get(s, str(s)), l) for s, l in game.created]
                    game.touch(128, 178)               # RUN
                    for _ in range(40):
                        game.key("a")
                        if game.in_field():
                            break
                    else:
                        note = "could not get back from a battle (a trainer or a scripted fight?)"
                        game.shot(os.path.join(out_dir, "wild_%s.png" % name))
                        break
                    found = [m for m in met if m[0] in table["land"] or m[0] in table["extra"]]
                    if not found:
                        wrong.append(met[0])
                    else:
                        m = found[0]
                        r["seen"].append("%s %d" % m)
                        if m[0] in table["land"] and m[1] not in table["land"][m[0]]:
                            wrong.append(m)
                if wrong:
                    r.update(result="failed", note="not in the table: %s" % wrong)
                elif note:
                    r.update(result="interrupted", note=note)
                elif not r["seen"]:
                    r.update(result="none", note="no wild Pokemon in %d steps" % steps)
                else:
                    r.update(result="ok")
        results.append(r)
        print("wild %-12s %-11s %s %s" % (name, r["result"], ", ".join(r["seen"]), r.get("note", "")), flush=True)


def features(game, state, data, world, names, out_dir, results):
    """The things the hack adds that need a place and a button press: the fossil reviver, the evolution item
    shop and its badge locks, and using Surf from the bag."""
    species, items = data["species"], data["items"]

    def record(name, problem, shot=True):
        results.append(dict(test="features", check=name, result="failed" if problem else "ok", note=problem or ""))
        if problem and shot:
            game.shot(os.path.join(out_dir, "feature_%s.png" % name.replace(" ", "_")))
        print("features %-28s %-6s %s" % (name, results[-1]["result"], problem or ""), flush=True)

    # fossil reviver: the scientist in the Ruins of Alph Research Center turns an Old Amber into an Aerodactyl
    lone = [battle_test.reference_party(data, 100)[0][1], 0, 0, 0, 0, 0]
    p = game.start(state, data, world, "D24R0102", (11, 5), facing=0, items=[items["OLD_AMBER"]], party=lone)
    if p is None:
        record("fossil reviver", "the Research Center did not load")
    else:
        for _ in range(50):
            game.key("a")
        # he asks the player to come back later, which the game tracks with a flag it clears on leaving the map
        game.set_flag(world.flags["FLAG_MAPTEMP_001"], False)
        game.created = []
        for _ in range(50):
            game.key("a")
            if game.created:
                break
        got = [s for s, _ in game.created]
        record("fossil reviver", None if species["AERODACTYL"] in got else "no Aerodactyl (created: %s)" % game.created[:3])

    # the evolution item shop on the Goldenrod Department Store's fourth floor: buy the item at each position
    # in the list and see what arrives, with no badges and with all of them
    wanted = {0: ["FIRE_STONE", "OVAL_STONE"], 16: ["FIRE_STONE", "SHINY_STONE", "PEAT_BLOCK", "RAZOR_FANG"]}
    locked = {0: ["SHINY_STONE", "PEAT_BLOCK", "RAZOR_FANG"], 16: []}
    names_by_id = {v: k for k, v in items.items()}
    for badges in (0, 16):
        stock = []
        for index in range(48):
            p = game.start(state, data, world, "T25R1004", (21, 7), facing=3, badges=badges)
            if p is None:
                break
            for _ in range(4):               # talk, his greeting, BUY
                game.key("a")
            game.run(150)
            # the stock is shown six to a page, in two columns
            for _ in range(index // 6):
                game.touch(60, 176, after=40)        # the next-page arrow
            game.touch(64 + 126 * (index % 2), 55 + 40 * (index % 6 // 2), after=40)
            game.added = []
            for _ in range(16):              # one of it, yes
                game.key("a")
                if game.added:
                    break
            if not game.added:
                break
            bought = names_by_id.get(game.added[0][0], str(game.added[0][0]))
            if index >= 6 and bought == stock[index - 6]:
                break                        # the arrow stayed on the last page: the list has ended
            stock.append(bought)
        missing = [w for w in wanted[badges] if w not in stock]
        early = [l for l in locked[badges] if l in stock]
        problem = None
        if not stock:
            problem = "could not buy anything"
        elif missing or early:
            problem = "missing %s, too early %s (stock: %s)" % (missing, early, stock)
        record("evolution shop, %d badges" % badges, problem)
        results[-1]["stock"] = stock

    # Surf from the bag: with HM03 in the bag and no Pokemon that knows Surf, facing water and pressing A
    tiles, occupied, _ = world.tiles("T20")
    shore = None
    for (x, z), b in sorted(tiles.items()):
        if b == 0 and (x, z) not in occupied and tiles.get((x + 1, z)) in WATER and tiles.get((x + 2, z)) in WATER:
            shore = (x, z)
            break
    if shore is None:
        record("surf from the bag", "no shore found in New Bark Town", shot=False)
    else:
        p = game.start(state, data, world, "T20", shore, facing=3, items=[items["HM03"]])
        if p is None:
            record("surf from the bag", "New Bark Town did not load")
        else:
            game.key("right", hold=2, after=10)
            for _ in range(8):
                game.key("a")
            game.run(120)
            p = game.position()
            record("surf from the bag", None if p and p[1:3] == (shore[0] + 1, shore[1]) else
                   "the player is at %s, not on the water at %s" % (p and p[1:3], (shore[0] + 1, shore[1])))


TESTS = {"sweep": sweep, "legendaries": legendaries, "wild": wild, "features": features}


# ------------------------------------------------------------------ main

def main():
    args = sys.argv[1:]
    def option(name, default):
        if name in args:
            i = args.index(name)
            value = args[i + 1]
            del args[i:i + 2]
            return value
        return default
    jobs = int(option("--jobs", "1"))
    part = option("--part", None)
    only = option("--maps", None)
    rom, tree, dump, out_dir = args[:4]
    tests = args[4:] or list(TESTS)
    os.makedirs(out_dir, exist_ok=True)
    state = os.path.join(out_dir, "bedroom.dst")
    if "--make-state" in args:
        battle_test.Game(rom).make_state(state)
        return
    if not os.path.exists(state):
        # in a process of its own: the emulator does not survive being opened twice in one
        subprocess.run([sys.executable, __file__, rom, tree, dump, out_dir, "--make-state"], check=True)
    if part is None and jobs > 1:
        procs = [subprocess.Popen([sys.executable, __file__, rom, tree, dump, out_dir] + tests
                                  + ["--part", "%d/%d" % (k, jobs)] + (["--maps", only] if only else []))
                 for k in range(jobs)]
        for p in procs:
            p.wait()
        merged = []
        for k in range(jobs):
            path = os.path.join(out_dir, "walk_results_%d.json" % k)
            if os.path.exists(path):
                merged += json.load(open(path))
    else:
        k, n = map(int, part.split("/")) if part else (0, 1)
        world = World(rom, tree, dump)
        data = battle_test.load(tree)
        game = Walker(rom)
        names = sorted(world.map_ids, key=world.map_ids.get)
        if only:
            names = [m for m in names if m in only.split(",")]
        merged = []
        for test in tests:
            if test == "features" and k != 0:
                continue                 # not per map: the first worker does it
            TESTS[test](game, state, data, world, names[k::n], out_dir, merged)
            json.dump(merged, open(os.path.join(out_dir, "walk_results_%d.json" % k), "w"), indent=1)
        if part:
            return
    json.dump(merged, open(os.path.join(out_dir, "walk_results.json"), "w"), indent=1)
    for test in tests:
        mine = [r for r in merged if r["test"] == test]
        counts = {}
        for r in mine:
            counts[r["result"]] = counts.get(r["result"], 0) + 1
        print("%s: %d checks: %s" % (test, len(mine), ", ".join("%d %s" % (v, k) for k, v in sorted(counts.items()))))


if __name__ == "__main__":
    main()
