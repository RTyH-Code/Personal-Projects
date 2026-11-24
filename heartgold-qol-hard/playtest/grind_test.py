#!/usr/bin/env python3
"""A long grind in one area, measured in the game.

    grind_test.py TEST_ROM TREE DUMP OUT MAP LEVEL BATTLES

TEST_ROM, TREE and DUMP are as for walk_test.py (a build with the test
harness). The harness puts its reference party at LEVEL on a grass tile of
MAP as far as can be from the map's trainers, and the party fights BATTLES
wild Pokemon there, as a player grinding would:

- each turn the Pokemon out uses its first move that still has PP (a move
  the game refuses is passed over);
- when one faints, the next one still standing is sent in (the party list
  and the Shift screen after it are told apart by the Shift screen's wide
  green button);
- a move to learn on a level-up is turned down, so the sets stay the same;
- between battles the party is healed, as at a Pokemon Center, but only
  when every one of its Pokemon reads in memory (stale copies of the party
  lie about, some with a slot overwritten).

Each battle goes to OUT/grind.jsonl: the wild Pokemon and its level, the
turns, the party's experience gained against level_curve.py's formula for
the Pokemon out at the end, faints, and the party's levels. A summary is
printed: battles won, experience measured against predicted, levels gained.
The grind stops early if the party whites out.
"""
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
import battle_test
import level_curve
import pkm
import walk_test as w

SHIFT_GREEN = lambda c: c[1] > 130 and c[0] < 120 and c[2] < 150
FORGET_PURPLE = (168, 104, 240)


def grass_tile(world, name):
    """A grass tile with grass beside it, as far as can be from every trainer standing on the map."""
    tiles, occupied, events = world.tiles(name)
    trainers = [(e["x"], e["z"]) for e in events.get("object_events", []) if "TRAINER" in str(e.get("script", ""))]
    best = None
    for t, b in tiles.items():
        if b not in w.GRASS or t in occupied:
            continue
        beside = [d for d, (dx, dz, _) in w.DIRS.items() if tiles.get((t[0] + dx, t[1] + dz)) in w.GRASS]
        if not beside:
            continue
        far = min((abs(t[0] - x) + abs(t[1] - z) for x, z in trainers), default=99)
        if best is None or far > best[0]:
            best = (far, t, beside)
    return best


def party(g):
    """(address, [Mon]) of a whole party in memory: u32 max count (6), u32 count, then that many Pokemon that all
    read; or (None, [])."""
    ram = bytes(g.emu.memory.unsigned[0x02000000:0x02400000])
    at = ram.find(struct.pack("<I", 6))
    while at >= 0:
        count = struct.unpack_from("<I", ram, at + 4)[0] if at + 8 <= len(ram) else 0
        if at % 4 == 0 and 0 < count <= 6:
            mons = [pkm.Mon(ram[at + 8 + pkm.PARTY_SIZE * i:at + 8 + pkm.PARTY_SIZE * (i + 1)]) for i in range(count)]
            if all(m.valid() and m.species and 0 < m.level <= 100 for m in mons):
                return 0x02000000 + at, mons
        at = ram.find(struct.pack("<I", 6), at + 1)
    return None, []


def heal(g):
    """Full HP, no status, PP back, for the whole party; True if done."""
    mem = g.emu.memory.unsigned
    for _ in range(20):
        at, mons = party(g)
        if at is not None:
            for i, m in enumerate(mons):
                top = struct.unpack_from("<H", m.stats, 8)[0]
                m.stats[0:4] = b"\0\0\0\0"
                struct.pack_into("<H", m.stats, 6, top)
                for k in range(4):          # block B: moves (u16) at 0x20, their PP (u8) at 0x28
                    m.blocks[0x28 + k] = 20 if m.u16(0x20 + 2 * k) else 0
                for k, b in enumerate(m.encode()):
                    mem[at + 8 + pkm.PARTY_SIZE * i + k] = b
            return True
        g.run(10)
    return False


def fight(g):
    """Play one wild battle from its first menu to the field. Returns (turns, faints, whited out)."""
    move = turns = faints = 0
    shift_pending = False
    start = g.position()
    for _ in range(900):
        image = g.emu.screenshot()
        state = battle_test.screen_state(image)
        px = lambda xy: image.getpixel(xy)[:3]
        if state == "menu":
            turns += 1
            g.touch(128, 73, after=40)
            g.touch(*battle_test.MOVE_BUTTONS[move], after=90)
        elif state == "moves":                  # still on the move list: refused (no PP), so the next one
            move = (move + 1) % 4
            g.touch(*battle_test.MOVE_BUTTONS[move], after=90)
        elif state in ("party", "confirm"):
            if SHIFT_GREEN(px((128, 215))) and SHIFT_GREEN(px((128, 250))):
                g.touch(128, 100, after=90)     # the Shift screen of the one chosen
                shift_pending = False
            else:
                slots = [battle_test.party_slot(image, i) for i in range(6)]
                alive = [i for i in range(1, 6) if slots[i] == "alive"]
                if "fainted" in slots and alive and not shift_pending:
                    faints += 1
                    move = 0
                    g.touch(*battle_test.PARTY_SLOTS[alive[0]], after=60)
                    shift_pending = True
                else:
                    g.run(20)
        elif px((8, 206)) == FORGET_PURPLE and px((240, 206)) == FORGET_PURPLE:
            g.touch(238, 172, after=60)         # which move to forget: back, keep the set
        else:
            g.key("a", after=30)
            if not battle_test.screen_state(g.emu.screenshot()) and g.in_field() and g.in_field():
                break
        g.run(20)
    here = g.position()
    whited = bool(here and start and here[0] != start[0])
    return turns, faints, whited


def main():
    rom, tree, dump, out, name, level, count = sys.argv[1:8]
    level, count = int(level), int(count)
    os.makedirs(out, exist_ok=True)
    state = os.path.join(out, "bedroom.dst")
    if not os.path.exists(state):
        battle_test.Game(rom).make_state(state)
    world = w.World(rom, tree, dump)
    data = battle_test.load(tree)
    base = {k: int(v) for k, v in re.findall(r"\[SPECIES_(\w+)\s*\] = (\d+)",
                                             open(os.path.join(tree, "data/BaseExperienceTable.c")).read())}
    names = {v: k for k, v in data["species"].items()}
    far, tile, beside = grass_tile(world, name)
    g = w.Walker(rom)
    where = g.start(state, data, world, name, tile, level=level, badges=8)
    print("on %s at %s, trainers at least %d tiles away" % (name, where, far), flush=True)
    _, mons = party(g)
    start_levels = [m.level for m in mons]
    there = beside[0]
    back = {"up": "down", "down": "up", "left": "right", "right": "left"}[there]
    log = open(os.path.join(out, "grind.jsonl"), "w")
    done = won = steps = measured = predicted = 0
    while done < count and steps < 20000:
        g.created = []
        g.step(there if steps % 2 == 0 else back)
        steps += 1
        if not g.created:
            continue
        wild, wild_level = names.get(g.created[0][0], str(g.created[0][0])), g.created[0][1]
        _, before = party(g)
        exp_before = {m.pid: m.u32(0x08) for m in before}
        for _ in range(100):                    # the battle's first menu
            g.run(20)
            if battle_test.screen_state(g.emu.screenshot()) == "menu":
                break
        turns, faints, whited = fight(g)
        _, after = party(g)
        gain = sum(m.u32(0x08) - exp_before.get(m.pid, m.u32(0x08)) for m in after) if before and after else None
        lead_level = after[0].level if after else level
        expect = level_curve.exp_gain(base.get(wild, 0), wild_level, lead_level, trainer=False) * \
            level_curve.MULTIPLIER
        record = dict(map=name, wild=wild, level=wild_level, turns=turns, faints=faints, exp=gain,
                      predicted=expect, whited_out=whited, party_levels=[m.level for m in after])
        log.write(json.dumps(record) + "\n")
        log.flush()
        print(record, flush=True)
        done += 1
        if whited:
            print("the party whited out; stopping", flush=True)
            break
        won += 1
        if gain is not None:
            measured += gain
            predicted += expect
        heal(g)
    _, mons = party(g)
    print("%d battles, %d won; experience %d measured against %d predicted; levels %s -> %s" % (
        done, won, measured, predicted, start_levels, [m.level for m in mons]), flush=True)


if __name__ == "__main__":
    main()
