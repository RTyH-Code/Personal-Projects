#!/usr/bin/env python3
"""Check faster breeding (tools/hack/faster_breeding.py) in the emulator.

    breed_test.py TEST_ROM TREE DUMP OUT

TEST_ROM, TREE and DUMP are as for walk_test.py (a build with the test harness). On Route 34 the player leaves
a Ditto and a Magikarp with the Day-Care Lady, then walks up and down inside the Day Care:

- the egg: the game makes one (GenerateEggPID, hooked) within the first 256 steps. The Day Care checks every
  256 steps; in the original game a Ditto and a Magikarp from the same trainer had a 20% chance each time;
- the hatch: the Day-Care Man outside hands the egg over, and the player walks again. A Magikarp egg has 5 egg
  cycles, one taken every 255 steps in the original game, so it can't hatch before step 1,276; taking two at
  a time it hatches by step 1,020. The test passes if it hatches within 1,100 steps.

Prints PASS or FAIL for each, with screenshots in OUT.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import struct

import grind_test
import pkm
import story_bot

GENERATE_EGG_PID = 0x0206C274
HOUSE, LADY_STAND, MAN = "R34R0101", (3, 6), 10          # stand below the lady at (3, 5); the man is object 10 of R34
EGG_STEPS, HATCH_STEPS = 300, 1100


class Tester:
    def __init__(self, rom, tree, dump, out, state):
        self.bot = story_bot.Bot(rom, tree, dump, out)
        self.g, self.world, self.data = self.bot.game, self.bot.world, self.bot.data
        self.state, self.out = state, out
        self.eggs = 0
        self.steps = 0
        self.g.emu.memory.register_exec(GENERATE_EGG_PID, self._egg)
        sp = self.data["species"]
        self.ours = {sp["DITTO"], sp["MAGIKARP"], sp["PIDGEY"], sp["PIDGEOTTO"]}

    def _egg(self, address, size):
        self.eggs += 1

    def shot(self, name):
        self.g.emu.screenshot().save(os.path.join(self.out, name + ".png"))

    def party(self):
        """The party. In the field it often fails its checksum (see qol_test.py), so a party whose blocks decode
        to the species this test uses (Ditto, Magikarp, Pidgey, Pidgeotto, an egg of them) is taken too."""
        _, mons = grind_test.party(self.g)
        if mons:
            return mons
        ram = bytes(self.g.emu.memory.unsigned[0x02000000:0x02400000])
        best = []
        at = ram.find(struct.pack("<I", 6))
        while at >= 0:
            count = struct.unpack_from("<I", ram, at + 4)[0] if at + 8 <= len(ram) else 0
            if at % 4 == 0 and 0 < count <= 6:
                mons = [pkm.Mon(ram[at + 8 + pkm.PARTY_SIZE * i:at + 8 + pkm.PARTY_SIZE * (i + 1)]) for i in range(count)]
                if all(m.species in self.ours for m in mons) and len(mons) > len(best):
                    best = mons             # the largest such record: smaller ones are a battle's or a menu's
            at = ram.find(struct.pack("<I", 6), at + 1)
        return best

    def pace_tiles(self):
        """Two open tiles side by side in the Day Care, away from the lady and the door."""
        tiles, occupied, _ = self.world.tiles(HOUSE)
        for (x, z) in sorted(tiles, key=lambda t: (-t[1], t[0])):
            if (x, z) in occupied or (x + 1, z) in occupied or (x + 1, z) not in tiles or z >= 11:
                continue
            return (x, z), (x + 1, z)
        return None

    def pace(self, limit, done):
        """Walk back and forth inside the Day Care until done() or `limit` steps. Returns the steps walked."""
        a, b = self.pace_tiles()
        self.bot.walk(HOUSE, {a: "left"})
        walked = 0
        while walked < limit and not done():
            here = self.g.position()
            self.g.step("right" if here and (here[1], here[2]) == a else "left")
            after = self.g.position()
            if here and after and here[1:3] != after[1:3]:
                walked += 1
                if walked % 100 == 0:
                    print("  %d steps" % walked, flush=True)
            elif not self.bot.free():
                self.bot.settle(["b"])          # the hatching scene: No to a nickname
        return walked

    def run(self):
        sp = self.data["species"]
        p = self.g.start(self.state, self.data, self.world, HOUSE, LADY_STAND, facing=0, level=20,
                         flags=["FLAG_GOT_BAG"],
                         party=[sp["DITTO"], sp["MAGIKARP"]] + [sp["PIDGEY"]] * 4)
        if p is None:
            return [("deposit", False, "the harness did not put the player in the Day Care")]
        self.bot.fs = None
        self.g.key("up", hold=2, after=20)
        for _ in range(40):                       # Yes, the first Pokemon, Store; Yes to another, the first, Store
            self.g.key("a", after=50)
            self.g.run_every_frame(30)
            if len(self.party()) == 4:
                break
        for _ in range(6):
            self.g.key("b", after=40)
        self.bot.settle(["b"])
        left = self.party()
        if len(left) != 4 or any(m.species in (sp["DITTO"], sp["MAGIKARP"]) for m in left):
            self.shot("deposit")
            return [("deposit", False, "the party is %s after the Day Care" % [m.species for m in left])]
        results = [("deposit", True, "Ditto and Magikarp left with the Day-Care Lady")]
        print("deposited", flush=True)

        self.eggs = 0
        walked = self.pace(EGG_STEPS, lambda: self.eggs > 0)
        results.append(("egg", self.eggs > 0 and walked <= 256,
                        "an egg after %d steps" % walked if self.eggs else "no egg in %d steps" % walked))
        if not self.eggs:
            self.shot("egg")
            return results

        self.bot.travel("R34")
        self.bot.talk("R34", MAN, answers=["a"])           # Yes, take the egg
        self.bot.settle(["a"])
        eggs = [m for m in self.party() if m.is_egg]
        if not eggs:
            self.shot("man")
            results.append(("hatch", False, "the Day-Care Man gave no egg"))
            return results
        self.bot.travel(HOUSE)
        def hatched():
            mons = self.party()
            return bool(mons) and not any(m.is_egg for m in mons)
        walked = self.pace(HATCH_STEPS, hatched)
        ok = hatched()
        if not ok:
            self.shot("hatch")
        results.append(("hatch", ok, "hatched after %d steps" % walked if ok else "not hatched in %d steps" % walked))
        return results


def main():
    rom, tree, dump, out = sys.argv[1:5]
    os.makedirs(out, exist_ok=True)
    state = os.path.join(out, "bedroom.dst")
    if not os.path.exists(state):
        subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r); import battle_test; "
                        "battle_test.Game(%r).make_state(%r)" % (HERE, rom, state)], check=True)
    results = Tester(rom, tree, dump, out, state).run()
    for name, ok, note in results:
        print("%-8s %s  %s" % (name, "PASS" if ok else "FAIL", note), flush=True)
    sys.exit(0 if all(ok for _, ok, _ in results) else 1)


if __name__ == "__main__":
    main()
