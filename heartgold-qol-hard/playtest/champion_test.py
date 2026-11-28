#!/usr/bin/env python3
"""Check in the emulator that what HeartGold unlocks with the National Dex now waits for the Champion (patch 0002).

    champion_test.py TEST_ROM TREE DUMP OUT

TEST_ROM, TREE and DUMP are as for walk_test.py (a build with the test harness). The hack gives the National Dex
from the start, and points the game's post-game checks at a new HasBecomeChampion (FLAG_GAME_CLEAR) instead.
Each check here is played twice, with FLAG_GAME_CLEAR clear and set:

- Cliff Cave: its map script moves the four Rock Smash rocks out of the way unless the check passes
  (nat_dex_flag_action, the script command the Supreme Cup and the Safari Zone gate use too);
- the Bug-Catching Contest: entering it at the Route 36 gate runs the contest's own check (in overlay 24), which
  decides its encounters, contestants and first prize. The test reads what that check returns. The contest is
  held on Tuesdays, Thursdays and Saturdays only (the emulator keeps the computer's date), so on other days
  this is skipped.

Prints PASS, FAIL or SKIP for each, with screenshots in OUT.
"""
import datetime
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import story_bot
from walk_test import DIRS

CONTEST_CHECK_RETURN = 0x022598F6      # the instruction after overlay 24's call to HasBecomeChampion
CLIFF_CAVE, GATE, OFFICER = "D50R0101", "R36R0201", (1, 7)       # below the contest officer at (1, 6)


class Tester:
    def __init__(self, rom, tree, dump, out, state):
        self.bot = story_bot.Bot(rom, tree, dump, out)
        self.g, self.world, self.data = self.bot.game, self.bot.world, self.bot.data
        self.state, self.out = state, out
        self.returns = []
        self.g.emu.memory.register_exec(CONTEST_CHECK_RETURN, self._contest_check)

    def _contest_check(self, address, size):
        self.returns.append(self.g.emu.memory.register_arm9.r0 & 0xFFFFFFFF)

    def start(self, name, tile, facing, champion):
        flags = ["FLAG_GOT_BAG"] + (["FLAG_GAME_CLEAR"] if champion else [])
        clear = [] if champion else ["FLAG_GAME_CLEAR"]
        p = self.g.start(self.state, self.data, self.world, name, tile, facing=facing, flags=flags,
                         clear_flags=clear)
        self.bot.fs = None
        self.g.run(60)
        return p

    def check_cliff_cave(self):
        events = self.world.events(CLIFF_CAVE).get("object_events", [])
        rocks = {i: (e["x"], e["z"]) for i, e in enumerate(events) if e.get("graphics_id") == "SPRITE_BREAKROCK"}
        tile = self.world.landing(CLIFF_CAVE)[0]
        seen = {}
        for champion in (False, True):
            if self.start(CLIFF_CAVE, tile, 1, champion) is None:
                return False, "the harness did not put the player in Cliff Cave"
            now = self.bot.objects()
            seen[champion] = sum(1 for i, xz in rocks.items() if now.get(i) == xz)
        ok = seen[False] == 0 and seen[True] == len(rocks)
        return ok, "rocks in place: %d of %d before the Champion, %d of %d after" % (
            seen[False], len(rocks), seen[True], len(rocks))

    def check_contest(self):
        if datetime.date.today().weekday() not in (1, 3, 5):
            return None, "no contest today (Tuesdays, Thursdays and Saturdays only)"
        got = {}
        for champion in (False, True):
            if self.start(GATE, OFFICER, 0, champion) is None:
                return False, "the harness did not put the player in the gate"
            self.returns = []
            self.g.key("up", hold=2, after=20)
            for _ in range(40):          # talk, and Yes to every question: enter, the others held, ready
                self.g.key("a", after=40)
                self.g.run_every_frame(20)
                if self.returns:
                    break
            got[champion] = self.returns[:1]
            if not self.returns:
                self.g.emu.screenshot().save(os.path.join(self.out, "contest_%s.png" % champion))
        ok = got[False] == [0] and bool(got[True]) and got[True][0] != 0
        return ok, "the contest's check returned %s before the Champion, %s after" % (got[False], got[True])


def main():
    rom, tree, dump, out = sys.argv[1:5]
    os.makedirs(out, exist_ok=True)
    state = os.path.join(out, "bedroom.dst")
    if not os.path.exists(state):
        subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r); import battle_test; "
                        "battle_test.Game(%r).make_state(%r)" % (HERE, rom, state)], check=True)
    t = Tester(rom, tree, dump, out, state)
    failed = False
    for name in ("cliff_cave", "contest"):
        ok, note = getattr(t, "check_" + name)()
        failed |= ok is False
        print("%-10s %s  %s" % (name, {True: "PASS", False: "FAIL", None: "SKIP"}[ok], note), flush=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
