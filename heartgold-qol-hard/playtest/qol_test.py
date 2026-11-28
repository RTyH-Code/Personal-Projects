#!/usr/bin/env python3
"""Check this round's quality-of-life changes in the emulator: the free Move Reminders (move_reminder.py), the
training items used from the bag (training_items.py), the trade evolutions by item and at Lv. 37
(trade_evos.py) and Voltorb on Route 38 (voltorb_wild.py).

    qol_test.py TEST_ROM TREE DUMP OUT [CHECK ...]

TEST_ROM, TREE and DUMP are as for walk_test.py (a build with the test harness). The checks:

- reminder: the woman in Cherrygrove City's Pokemon Center makes a Pokemon that knows only Tackle remember a
  move, with no Heart Scale in the bag;
- maniac: Blackthorn City's Move Maniac does the same, on first meeting him, with no Heart Scale;
- bottle cap: a Bottle Cap makes the lead's lowest IV 31 and leaves the others, and its stat goes up;
- gold bottle cap: a Gold Bottle Cap makes all six IVs 31;
- mint: an Adamant Mint (a Modest Mint if the lead is Adamant already) raises Attack or lowers Sp. Atk, or both;
- king's rock: used on a Slowpoke, it evolves into Slowking;
- level 37: a Rare Candy on a Lv. 36 Kadabra evolves it into Alakazam;
- voltorb: Voltorb is among the first 60 wild Pokemon on Route 38.

CHECK names some of them (such as bottle_cap). Prints PASS or FAIL for each, with screenshots in OUT.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import battle_test
import grind_test
import walk_test as w

MENU, BAG_ICON = (84, 8), (44, 113)                 # the touch screen's MENU tab, and the Bag in it
POCKETS = {"items": (14, 16), "medicine": (46, 16)}     # the tabs along the top of the touch screen
FIRST_SLOT, USE, LEAD = (64, 56), (48, 142), (60, 32)
STAT_NAMES = ["HP", "Attack", "Defense", "Speed", "Sp. Atk", "Sp. Def"]


def ivs(mon):
    return [(mon.u32(0x30) >> (5 * i)) & 31 for i in range(6)]


def stats(mon):
    """Max HP, Attack, Defense, Speed, Sp. Atk, Sp. Def."""
    return [mon.stats[8 + 2 * i] | mon.stats[9 + 2 * i] << 8 for i in range(6)]


def moves(mon):
    return [mon.u16(0x20 + 2 * i) for i in range(4)]


class Tester:
    def __init__(self, rom, tree, dump, out, state):
        self.g = w.Walker(rom)
        self.world = w.World(rom, tree, dump)
        self.data = battle_test.load(tree)
        self.state, self.out = state, out
        ids = self.data["boss_teams"].MOVE_IDS
        self.tackle = ids.get("TACKLE", ids.get("MOVE_TACKLE"))

    def lead(self):
        for _ in range(10):
            _, mons = grind_test.party(self.g)
            if mons:
                return mons[0]
            self.g.run(30)
        return None

    def start(self, name, tile, facing=1, items=(), party=None, level=100, lead_moves=None):
        p = self.g.start(self.state, self.data, self.world, name, tile, facing=facing, flags=["FLAG_GOT_BAG"],
                         items=[self.data["items"][i] for i in items], level=level, lead_moves=lead_moves,
                         party=[self.data["species"][s] for s in party] if party else None)
        self.g.run(60)
        return p

    def use_on_lead(self, pocket, wait=200, leave="b"):
        """From the field: the Bag, the first item of a pocket, Use, on the lead; then through the messages.
        Returns the lead as it was, read on the party screen. (Straight after the harness's warp the party in
        memory doesn't pass its checksum; it does once the party screen has opened.) The messages are closed
        with `leave`: B, as A would go on to use the item again; but A where an evolution follows, as B stops it."""
        g = self.g
        g.touch(*MENU, after=60)
        g.touch(*BAG_ICON, after=30)
        g.run_every_frame(90)
        if pocket != "items":
            g.touch(*POCKETS[pocket], after=30)
            g.run_every_frame(30)
        g.touch(*FIRST_SLOT, after=30)
        g.run_every_frame(30)
        g.touch(*USE, after=30)
        g.run_every_frame(90)
        before = self.lead()
        g.touch(*LEAD, after=30)
        for _ in range(wait // 20):
            g.run_every_frame(20)
        for _ in range(6):
            g.key(leave, after=40)
        return before

    def shot(self, name):
        self.g.emu.screenshot().save(os.path.join(self.out, "%s.png" % name))

    # ------------------------------------------------------------------ the checks

    def relearn(self, name, tile, facing, turn, label):
        if self.start(name, tile, facing=facing, lead_moves=[self.tackle, 0, 0, 0]) is None:
            return False, "the harness did not put the player in %s" % name
        before = [self.tackle, 0, 0, 0]          # what the harness gave the lead
        self.g.key(turn, hold=2, after=20)
        after = None
        for _ in range(30):
            self.g.key("a", after=50)
            self.g.run_every_frame(30)
            _, mons = grind_test.party(self.g)
            if mons and moves(mons[0]) != before:
                after = mons[0]
                break
        else:
            self.shot(label)
        for _ in range(6):
            self.g.key("b", after=40)
        gained = [m for m in moves(after) if m and m not in before] if after else []
        return bool(gained), "moves %s -> %s" % (before, moves(after) if after else "unchanged")

    def check_reminder(self):
        return self.relearn("T21PC0101", (2, 10), 2, "left", "reminder")

    def check_maniac(self):
        return self.relearn("T30R0601", (3, 5), 0, "up", "maniac")

    def check_bottle_cap(self):
        self.start("R29", self.world.landing("R29")[0], items=["BOTTLE_CAP"])
        before = self.use_on_lead("items")
        after = self.lead()
        if not before or not after:
            return False, "no party"
        b, a = ivs(before), ivs(after)
        low = b.index(min(b))
        expect = [31 if i == low else v for i, v in enumerate(b)]
        ok = a == expect and stats(after)[low] > stats(before)[low]
        if not ok:
            self.shot("bottle_cap")
        return ok, "IVs %s -> %s; %s %d -> %d" % (b, a, STAT_NAMES[low], stats(before)[low], stats(after)[low])

    def check_gold_bottle_cap(self):
        self.start("R29", self.world.landing("R29")[0], items=["GOLD_BOTTLE_CAP"])
        before = self.use_on_lead("items")
        after = self.lead()
        if not before or not after:
            return False, "no party"
        ok = ivs(after) == [31] * 6
        if not ok:
            self.shot("gold_bottle_cap")
        return ok, "IVs %s -> %s" % (ivs(before), ivs(after))

    def check_mint(self):
        # the lead is the same Pokemon each time (the same save state and harness), and not Adamant: a Modest
        # Mint is the fallback for a harness whose lead is Adamant already
        mint = os.environ.get("QOL_MINT", "ADAMANT_MINT")
        self.start("R29", self.world.landing("R29")[0], items=[mint])
        before = self.use_on_lead("medicine")
        if before and before.pid % 25 == 3 and mint == "ADAMANT_MINT":        # 3 is Adamant
            return False, "the lead is Adamant already: run with QOL_MINT=MODEST_MINT"
        after = self.lead()
        if not before or not after:
            return False, "no party"
        (ba, bs), (aa, as_) = (stats(before)[1], stats(before)[4]), (stats(after)[1], stats(after)[4])
        if mint == "ADAMANT_MINT":
            ok = aa >= ba and as_ <= bs and (aa, as_) != (ba, bs)
        else:
            ok = aa <= ba and as_ >= bs and (aa, as_) != (ba, bs)
        if not ok:
            self.shot("mint")
        return ok, "%s: Attack %d -> %d, Sp. Atk %d -> %d" % (mint, ba, aa, bs, as_)

    def evolve(self, species, item, pocket, level, wanted, label):
        self.start("R29", self.world.landing("R29")[0], items=[item], party=[species] * 6, level=level)
        before = self.use_on_lead(pocket, wait=200, leave="a")
        # the evolution scene: let it play (B would stop it)
        for _ in range(60):
            self.g.run(30)
            self.g.key("a", after=10)
            mon = self.lead()
            if mon and mon.species == self.data["species"][wanted]:
                break
        after = self.lead()
        names = {v: k for k, v in self.data["species"].items()}
        ok = bool(after) and after.species == self.data["species"][wanted]
        if not ok:
            self.shot(label)
        return ok, "%s -> %s" % (names.get(before.species) if before else None, names.get(after.species) if after else None)

    def check_kings_rock(self):
        return self.evolve("SLOWPOKE", "KINGS_ROCK", "items", 30, "SLOWKING", "kings_rock")

    def check_level_37(self):
        return self.evolve("KADABRA", "RARE_CANDY", "medicine", 36, "ALAKAZAM", "level_37")

    def check_voltorb(self):
        far, tile, beside = grind_test.grass_tile(self.world, "R38")
        if self.start("R38", tile, level=50) is None:
            return False, "the harness did not put the player on Route 38"
        there = beside[0]
        back = {"up": "down", "down": "up", "left": "right", "right": "left"}[there]
        met, note = w.meet(self.g, there, back, 60, self.out, "voltorb")
        names = {v: k for k, v in self.data["species"].items()}
        seen = [names.get(s, str(s)) for s, _ in met]
        voltorb = [lv for s, lv in met if s == self.data["species"]["VOLTORB"]]
        return bool(voltorb), "%d of %d were Voltorb (Lv. %s) %s" % (len(voltorb), len(seen), sorted(set(voltorb)), note)


CHECKS = ["reminder", "maniac", "bottle_cap", "gold_bottle_cap", "mint", "kings_rock", "level_37", "voltorb"]


def main():
    rom, tree, dump, out = sys.argv[1:5]
    only = sys.argv[5:] or CHECKS
    os.makedirs(out, exist_ok=True)
    state = os.path.join(out, "bedroom.dst")
    if not os.path.exists(state):
        # making the state and then a Walker in one process can crash the emulator: make it in its own
        subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r); import battle_test; "
                        "battle_test.Game(%r).make_state(%r)" % (HERE, rom, state)], check=True)
    t = Tester(rom, tree, dump, out, state)
    results = []
    for name in [c for c in CHECKS if c in only]:
        ok, note = getattr(t, "check_" + name)()
        results.append(ok)
        print("%-16s %s  %s" % (name, "PASS" if ok else "FAIL", note), flush=True)
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
