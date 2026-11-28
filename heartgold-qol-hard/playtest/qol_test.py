#!/usr/bin/env python3
"""Check this round's quality-of-life changes in the emulator: the free Move Reminders (move_reminder.py), the
training items used from the bag (training_items.py, hyper_training.py), the trade evolutions by item and at Lv. 37
(trade_evos.py) and Voltorb on Route 38 (voltorb_wild.py).

    qol_test.py TEST_ROM TREE DUMP OUT [CHECK ...]

TEST_ROM, TREE and DUMP are as for walk_test.py (a build with the test harness). The checks:

- reminder: the woman in Cherrygrove City's Pokemon Center makes a Pokemon that knows only Tackle remember a
  move, with no Heart Scale in the bag;
- maniac: Blackthorn City's Move Maniac does the same, on first meeting him, with no Heart Scale;
- hyper speed: the hyper trainer on Goldenrod 5F (hyper_training.py), for a Bottle Cap, makes the lead's Speed IV
  31 and leaves the others;
- hyper maxed: asked again for Speed, now 31, he changes nothing;
- hyper all: for a Gold Bottle Cap, "Every stat" makes all six IVs 31;
- mint: an Adamant Mint (a Modest Mint if the lead is Adamant already) raises Attack or lowers Sp. Atk, or both;
- king's rock: used on a Slowpoke, it evolves into Slowking;
- level 37: a Rare Candy on a Lv. 36 Kadabra evolves it into Alakazam;
- voltorb: Voltorb is among the first 60 wild Pokemon on Route 38;
- park bugs: Scyther and Pinsir are both among 120 wild Pokemon in the National Park (park_bugs.py).

CHECK names some of them (such as hyper_all). Prints PASS or FAIL for each, with screenshots in OUT.
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
# the hyper trainer's stat menu, two columns on the touch screen: the keys to each button
# (with the D-pad from HP, top left, as a touch right after the menu opens can be missed)
STAT_BUTTONS = {"HP": (), "Attack": ("right",), "Defense": ("down",), "Sp. Atk": ("right", "down"),
                "Sp. Def": ("down", "down"), "Speed": ("right", "down", "down"), "Every stat": ("down", "down", "down"),
                "Never mind": ("right", "down", "down", "down")}
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
        self.after = self.lead()            # still on the party screen, where the party reads reliably
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

    def hyper_train(self, button, items):
        """Ask the hyper trainer on Goldenrod 5F to train the lead: talk, the lead, then a button of the stat menu.
        Returns the lead before and after."""
        self.start("T25R1005", (21, 5), facing=0, items=items)
        self.g.key("up", hold=2, after=20)
        before = None
        for _ in range(12):                      # through his lines to the party, the lead, to the stat menu
            self.g.key("a", after=50)
            self.g.run_every_frame(30)
            if before is None:
                _, mons = grind_test.party(self.g)
                before = mons[0] if mons else None
            if self.menu_open():
                break
        self.g.run_every_frame(30)
        for key in button + ("a",):
            self.press(key)
        for _ in range(8):
            self.g.run_every_frame(40)
            self.g.key("a", after=40)
        return before, self.lead()

    def press(self, key):
        """A key press with every frame run: this menu misses presses made while frames are skipped."""
        self.g.emu.input.keypad_add_key(self.g.keys[key])
        self.g.run_every_frame(6)
        self.g.emu.input.keypad_rm_key(self.g.keys[key])
        self.g.run_every_frame(24)

    def menu_open(self):
        """The stat menu: eight pale buttons in two columns on the touch screen."""
        image = self.g.emu.screenshot()
        light = lambda x, y: min(image.getpixel((x, 192 + y))[:3]) > 180
        return all(light(x, y) for x in (40, 166) for y in (24, 72, 120, 168))

    def check_hyper_speed(self):
        before, after = self.hyper_train(STAT_BUTTONS["Speed"], ["BOTTLE_CAP"])
        if not before or not after:
            return False, "no party"
        b, a = ivs(before), ivs(after)
        expect = [31 if i == 3 else v for i, v in enumerate(b)]           # Speed is the fourth IV
        ok = a == expect and (b[3] == 31 or stats(after)[3] > stats(before)[3])
        if not ok:
            self.shot("hyper_speed")
        return ok, "IVs %s -> %s; Speed %d -> %d" % (b, a, stats(before)[3], stats(after)[3])

    def check_hyper_maxed(self):
        # a stat at 31 already: nothing changes (the trainer says so and keeps the cap)
        before, after = self.hyper_train(STAT_BUTTONS["Speed"], ["BOTTLE_CAP"])
        if not before or not after:
            return False, "no party"
        before2, after2 = self.hyper_train_again(STAT_BUTTONS["Speed"])
        ok = after2 is not None and ivs(after2) == ivs(after)
        if not ok:
            self.shot("hyper_maxed")
        return ok, "a second try at Speed: IVs %s -> %s" % (ivs(after), ivs(after2) if after2 else None)

    def hyper_train_again(self, button):
        """Talk to him again without reloading (so a stat maxed a moment ago is still 31)."""
        self.g.key("up", hold=2, after=20)
        for _ in range(12):
            self.g.key("a", after=50)
            self.g.run_every_frame(30)
            if self.menu_open():
                break
        self.g.run_every_frame(30)
        for key in button + ("a",):
            self.press(key)
        for _ in range(8):
            self.g.run_every_frame(40)
            self.g.key("a", after=40)
        return None, self.lead()

    def check_hyper_all(self):
        before, after = self.hyper_train(STAT_BUTTONS["Every stat"], ["GOLD_BOTTLE_CAP"])
        if not before or not after:
            return False, "no party"
        ok = ivs(after) == [31] * 6
        if not ok:
            self.shot("hyper_all")
        return ok, "IVs %s -> %s" % (ivs(before), ivs(after))

    def check_mint(self):
        # the lead is the same Pokemon each time (the same save state and harness), and not Adamant: a Modest
        # Mint is the fallback for a harness whose lead is Adamant already
        mint = os.environ.get("QOL_MINT", "ADAMANT_MINT")
        self.start("R29", self.world.landing("R29")[0], items=[mint])
        before = self.use_on_lead("medicine")
        if before and before.pid % 25 == 3 and mint == "ADAMANT_MINT":        # 3 is Adamant
            return False, "the lead is Adamant already: run with QOL_MINT=MODEST_MINT"
        after = self.after or self.lead()
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

    def check_park_bugs(self):
        """Scyther (5%) and Pinsir (4%) in the National Park's own grass (park_bugs.py): both among 120 wild Pokemon
        (each is missed by chance less than one time in a hundred)."""
        far, tile, beside = grind_test.grass_tile(self.world, "D22R0101")
        if self.start("D22R0101", tile, level=50) is None:
            return False, "the harness did not put the player in the National Park"
        there = beside[0]
        back = {"up": "down", "down": "up", "left": "right", "right": "left"}[there]
        met, note = w.meet(self.g, there, back, 120, self.out, "park_bugs")
        sp = self.data["species"]
        count = {name: sum(1 for s, _ in met if s == sp[name]) for name in ("SCYTHER", "PINSIR")}
        return all(count.values()), "of %d: %d Scyther, %d Pinsir %s" % (len(met), count["SCYTHER"], count["PINSIR"], note)


CHECKS = ["reminder", "maniac", "hyper_speed", "hyper_maxed", "hyper_all", "mint", "kings_rock", "level_37", "voltorb", "park_bugs"]


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
