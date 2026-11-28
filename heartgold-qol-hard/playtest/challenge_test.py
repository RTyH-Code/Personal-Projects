#!/usr/bin/env python3
"""Check the challenge rules (tools/hack/challenge_rules.py) in the emulator.

    challenge_test.py TEST_ROM TREE DUMP OUT

TEST_ROM, TREE and DUMP are as for walk_test.py (a build with the test harness). The checks:

- the rules NPC: in the player's house, talking to the woman by the right-hand wall and choosing
  "Level cap" turns the rule on (VAR_UNK_416F becomes 1), and choosing it again turns it off;
- the level cap: on Route 29 with no badges (the cap is Falkner's top level, 14), a Lv. 14 party leader
  gains no experience from a wild battle with the cap on, and does with it off;
- no items: in a trainer battle, choosing a potion from the bag goes on to "use on which Pokemon?" with
  the rule off, and doesn't with it on;
- exp share (tools/hack/party_exp_share.py): with the party at Lv. 14, a wild battle on Route 29 gives the second
  Pokemon nothing with the rule off, and with it on about half what the lead gets;
- share x2: the same over a whole trainer battle with two foes (Bird Keeper Rod), so the share is handed out
  again for the second.

Prints PASS or FAIL for each, and screenshots in OUT.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import battle_test
import grind_test
import walk_test as w

RULES = 0x416F
HOUSE, NPC_STAND = "T20R0201", (10, 7)          # left of the woman at (11, 7), facing right


def press_until(g, value, tries=14):
    """Press A (through her lines, and on the menu's first entry, the level cap) until the rules read value."""
    for _ in range(tries):
        g.key("a", after=60)
        if g.get_var(RULES) == value:
            return True
    return False


def check_npc(g, state, data, world, out):
    # past Mom's opening scene, which the bedroom save is from before
    if g.start(state, data, world, HOUSE, NPC_STAND, facing=3, badges=0,
               variables=[("VAR_SCENE_PLAYERS_HOUSE_1F", 1)]) is None:
        return False, "the harness did not place the player"
    g.key("right", hold=2, after=30)            # face her
    before = g.get_var(RULES)
    press_until(g, 1)                           # talk; "Level cap" turns it on
    on = g.get_var(RULES)
    g.emu.screenshot().save(os.path.join(out, "npc_on.png"))
    press_until(g, 0)                           # back at the menu; "Level cap" again turns it off
    off = g.get_var(RULES)
    for key in ("b", "a", "a", "a"):            # leave the menu, and her goodbye
        g.key(key, after=60)
    return (before, on, off) == (0, 1, 0), "the rules went %s -> %s -> %s" % (before, on, off)


def wild_exp(g, state, data, world, rules):
    """The Lv. 14 lead's experience gained over one wild battle on Route 29, with the rules set as given."""
    far, tile, beside = grind_test.grass_tile(world, "R29")
    if g.start(state, data, world, "R29", tile, level=14, badges=0, variables=[("VAR_UNK_416F", rules)]) is None:
        return None
    there = beside[0]
    back = {"up": "down", "down": "up", "left": "right", "right": "left"}[there]
    for steps in range(400):
        g.created = []
        g.step(there if steps % 2 == 0 else back)
        if g.created:
            break
    else:
        print("  no wild encounter", flush=True)
        return None
    _, before = grind_test.party(g)            # read once the battle has started, as grind_test.py does
    for _ in range(100):
        g.run(20)
        if battle_test.screen_state(g.emu.screenshot()) == "menu":
            break
    grind_test.fight(g)
    _, after = grind_test.party(g)
    if not before or not after:
        print("  party not found: %d before, %d after" % (len(before), len(after)), flush=True)
        return None
    gained = {m.pid: m.u32(0x08) for m in after}
    lead = before[0]
    return gained[lead.pid] - lead.u32(0x08) if lead.pid in gained else None


def share_exp(g, state, data, world, share):
    """(lead's, second Pokemon's) experience from one wild battle on Route 29, all at Lv. 14, with the party-wide
    exp share (VAR_UNK_416E) set as given."""
    far, tile, beside = grind_test.grass_tile(world, "R29")
    if g.start(state, data, world, "R29", tile, level=14, badges=0, variables=[("VAR_UNK_416E", share)]) is None:
        return None
    there = beside[0]
    back = {"up": "down", "down": "up", "left": "right", "right": "left"}[there]
    for steps in range(400):
        g.created = []
        g.step(there if steps % 2 == 0 else back)
        if g.created:
            break
    else:
        return None
    _, before = grind_test.party(g)
    for _ in range(100):
        g.run(20)
        if battle_test.screen_state(g.emu.screenshot()) == "menu":
            break
    grind_test.fight(g)
    _, after = grind_test.party(g)
    if len(before) < 2 or len(after) < 2:
        return None
    gained = {m.pid: m.u32(0x08) for m in after}
    return tuple(gained.get(m.pid, m.u32(0x08)) - m.u32(0x08) for m in before[:2])


def check_share(g, state, data, world):
    off, on = share_exp(g, state, data, world, 0), share_exp(g, state, data, world, 1)
    ok = (off is not None and on is not None and off[0] > 0 and off[1] == 0 and on[0] > 0
          and 0.4 * on[0] <= on[1] <= 0.6 * on[0])
    return ok, "lead and second Pokemon gained %s with the exp share off, %s with it on" % (off, on)


def share_trainer(g, state, data, share, trainer=29):
    """(lead's, second Pokemon's) experience from a whole trainer battle against two foes (Bird Keeper Rod's two
    Lv. 7 Pokemon), the party at Lv. 14, with the party-wide exp share set as given."""
    g.emu.savestate.load_file(state)
    g.vars_pointer, g.frames = None, 0
    g.run(40)
    party = battle_test.reference_party(data, 14)
    for i, (_, species_id, _, moves, item) in enumerate(party):
        g.set_var(0x4000 + i, species_id)
        g.set_var(0x4006 + i, 14)
        g.set_var(0x4010 + i, item)
        for j in range(4):
            g.set_var(0x4020 + 4 * i + j, moves[j] if j < len(moves) else 0)
    g.set_var(0x400E, 0)
    g.set_var(0x400C, trainer)
    g.set_var(0x400F, 0)
    g.set_var(0x416E, share)
    g.key("a")
    for _ in range(300):
        g.run(20)
        if battle_test.screen_state(g.emu.screenshot()) == "menu":
            break
    else:
        return None
    _, before = grind_test.party(g)
    # grind_test.fight plays wild battles: between the trainer's two Pokemon the game offers a switch, which it
    # takes to the party screen. Back out of that (keeping the lead in) and fight on, until the field returns
    for _ in range(4):
        grind_test.fight(g)
        if g.in_field():
            break
        for _ in range(3):
            if battle_test.screen_state(g.emu.screenshot()) != "party":
                break
            g.key("b", after=60)
        for _ in range(40):
            g.run(20)
            if battle_test.screen_state(g.emu.screenshot()) == "menu" or g.in_field():
                break
    after = []
    for _ in range(20):
        _, after = grind_test.party(g)
        if after:
            break
        g.run(30)
    if len(before) < 2 or len(after) < 2:
        return None
    gained = {m.pid: m.u32(0x08) for m in after}
    return tuple(gained.get(m.pid, m.u32(0x08)) - m.u32(0x08) for m in before[:2])


def check_share_trainer(g, state, data):
    off, on = share_trainer(g, state, data, 0), share_trainer(g, state, data, 1)
    ok = (off is not None and on is not None and off[0] > 0 and off[1] == 0 and on[0] > 0
          and 0.4 * on[0] <= on[1] <= 0.6 * on[0])
    return ok, "over a trainer's two Pokemon, lead and second Pokemon gained %s off, %s on" % (off, on)


def check_cap(g, state, data, world):
    capped, free = wild_exp(g, state, data, world, 1), wild_exp(g, state, data, world, 0)
    return capped == 0 and bool(free), "experience gained: %s with the cap, %s without" % (capped, free)


def potion_reaches_party(g, state, data, trainer, rules):
    """In a battle with `trainer`, does a potion from the bag get as far as choosing a Pokemon?"""
    g.emu.savestate.load_file(state)
    g.vars_pointer, g.frames = None, 0
    g.run(40)
    party = battle_test.reference_party(data, 30)
    for i, (_, species_id, _, moves, item) in enumerate(party):
        g.set_var(0x4000 + i, species_id)
        g.set_var(0x4006 + i, 30)
        g.set_var(0x4010 + i, item)
        for j in range(4):
            g.set_var(0x4020 + 4 * i + j, moves[j] if j < len(moves) else 0)
    g.set_var(0x4038, data["items"]["POTION"])     # five Potions (the harness gives these with the party)
    g.set_var(0x400E, 0)
    g.set_var(0x400C, trainer)
    g.set_var(0x400F, 0)
    g.set_var(RULES, rules)
    g.key("a")
    for _ in range(300):
        g.run(20)
        if battle_test.screen_state(g.emu.screenshot()) == "menu":
            break
    else:
        return None
    for xy, wait in (((36, 172), 200), ((64, 50), 150), ((64, 40), 200), ((110, 172), 120)):
        g.touch(*xy, after=wait)        # Bag, HP/PP restore, the first item, Use
    for _ in range(20):
        g.run(20)
        if battle_test.screen_state(g.emu.screenshot()) == "party":
            return True
    return False


def check_items(g, state, data):
    trainer = 2         # a Route 29-era trainer: any trainer battle will do
    allowed, blocked = potion_reaches_party(g, state, data, trainer, 0), potion_reaches_party(g, state, data, trainer, 2)
    return allowed is True and blocked is False, "potion reached the party screen: %s without the rule, %s with it" % (
        allowed, blocked)


def main():
    rom, tree, dump, out = sys.argv[1:5]
    os.makedirs(out, exist_ok=True)
    state = os.path.join(out, "bedroom.dst")
    if not os.path.exists(state):
        battle_test.Game(rom).make_state(state)
    world = w.World(rom, tree, dump)
    data = battle_test.load(tree)
    g = w.Walker(rom)
    g.run(400)
    results = []
    for name, check in (("rules NPC", lambda: check_npc(g, state, data, world, out)),
                        ("level cap", lambda: check_cap(g, state, data, world)),
                        ("no items", lambda: check_items(g, state, data)),
                        ("exp share", lambda: check_share(g, state, data, world)),
                        ("share x2", lambda: check_share_trainer(g, state, data))):
        ok, note = check()
        results.append((name, ok, note))
        print("%-10s %s  %s" % (name, "PASS" if ok else "FAIL", note), flush=True)
    sys.exit(0 if all(ok for _, ok, _ in results) else 1)


if __name__ == "__main__":
    main()
