#!/usr/bin/env python3
"""Check in the emulator that what HeartGold unlocks with the National Dex now waits for the Champion (patch 0002).

    champion_test.py TEST_ROM TREE DUMP OUT [CHECK ...]

TEST_ROM, TREE and DUMP are as for walk_test.py (a build with the test harness). The hack gives the National Dex
from the start, and points the game's post-game checks at a new HasBecomeChampion (FLAG_GAME_CLEAR) instead.
Each check here is played twice, with FLAG_GAME_CLEAR clear and set:

- Cliff Cave: its map script moves the four Rock Smash rocks out of the way unless the check passes
  (nat_dex_flag_action, the script command the Supreme Cup and the Safari Zone gate use too);
- the Bug-Catching Contest: entering it at the Route 36 gate runs the contest's own check (in overlay 24), which
  decides its encounters, contestants and first prize. The test reads what that check returns. The contest is
  held on Tuesdays, Thursdays and Saturdays only (the emulator keeps the computer's date), so on other days
  this is skipped;
- the Pokeathlon Dome's prize clerk: the checks for which prize list she shows and sells (in script commands
  834 and 771), read as they run;
- the Supreme Cup: the Friendship Room's first-visit scene shows its receptionist (clears
  FLAG_HIDE_POKEATHLON_SUPREME_CUP_RECEPTIONIST) only after the Champion.

The Hoenn and Sinnoh Sound radio shows and Baoba's later phone calls use the same check, but aren't played here.

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
PRIZE_LIST_RETURNS = {0x0204833E: "list shown", 0x0204823E: "list sold"}   # after the Pokeathlon prize shop's calls
DOME, CLERK = "D49R0101", (36, 9)      # below the Pokeathlon Dome's prize clerk at (36, 8)
FRIENDSHIP_ROOM = "D49R0107"
CLIFF_CAVE, GATE, OFFICER = "D50R0101", "R36R0201", (1, 7)       # below the contest officer at (1, 6)


class Tester:
    def __init__(self, rom, tree, dump, out, state):
        self.bot = story_bot.Bot(rom, tree, dump, out)
        self.g, self.world, self.data = self.bot.game, self.bot.world, self.bot.data
        self.state, self.out = state, out
        self.returns = []
        self.g.emu.memory.register_exec(CONTEST_CHECK_RETURN, self._contest_check)
        self.prizes = []
        for address, what in PRIZE_LIST_RETURNS.items():
            self.g.emu.memory.register_exec(address, (lambda what: lambda a, s: self.prizes.append(
                (what, self.g.emu.memory.register_arm9.r0 & 0xFFFFFFFF)))(what))

    def _contest_check(self, address, size):
        self.returns.append(self.g.emu.memory.register_arm9.r0 & 0xFFFFFFFF)

    def start(self, name, tile, facing, champion, flags=(), variables=()):
        flags = ["FLAG_GOT_BAG"] + list(flags) + (["FLAG_GAME_CLEAR"] if champion else [])
        clear = [] if champion else ["FLAG_GAME_CLEAR"]
        p = self.g.start(self.state, self.data, self.world, name, tile, facing=facing, flags=flags,
                         clear_flags=clear, variables=variables)
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


def check_pokeathlon(t):
    """The Pokeathlon Dome's prize clerk: talking runs the check for which prize list is shown, and Buy the one for
    which list is sold. Each should say no before the Champion and yes after."""
    got = {}
    for champion in (False, True):
        if t.start(DOME, CLERK, 0, champion, flags=["FLAG_UNK_114"]) is None:
            return False, "the harness did not put the player in the Pokeathlon Dome"
        t.prizes = []
        t.g.key("up", hold=2, after=20)
        for _ in range(25):           # talk, then the first choice (Buy)
            t.g.key("a", after=40)
            t.g.run_every_frame(20)
            if len({w for w, _ in t.prizes}) == 2:
                break
        got[champion] = dict(t.prizes)
        for _ in range(8):
            t.g.key("b", after=30)
        if len(got[champion]) < 2:
            t.g.emu.screenshot().save(os.path.join(t.out, "pokeathlon_%s.png" % champion))
    ok = all(got[False].get(w) == 0 and got[True].get(w) for w in PRIZE_LIST_RETURNS.values())
    return ok, "prize list checks before the Champion %s, after %s" % (got[False], got[True])


def check_supreme_cup(t):
    """The Friendship Room's first-visit scene shows the Supreme Cup's receptionist (clears her hidden flag) only
    once the player is Champion."""
    hidden = {}
    for champion in (False, True):
        if t.start(FRIENDSHIP_ROOM, (7, 13), 0, champion, flags=["FLAG_HIDE_POKEATHLON_SUPREME_CUP_RECEPTIONIST"],
                   variables=[("VAR_UNK_40D3", 0)]) is None:
            return False, "the harness did not put the player in the Friendship Room"
        t.bot.settle()
        hidden[champion] = t.bot.flag("FLAG_HIDE_POKEATHLON_SUPREME_CUP_RECEPTIONIST")
        scene = t.g.emu.memory.unsigned[t.g.vars_pointer + 2 * (t.world.vars["VAR_UNK_40D3"] - 0x4000)]
        hidden[champion] = (hidden[champion], scene)
    ok = hidden[False] == (True, 1) and hidden[True] == (False, 1)
    return ok, "after the scene (receptionist hidden, scene var): before the Champion %s, after %s" % (
        hidden[False], hidden[True])


def main():
    rom, tree, dump, out = sys.argv[1:5]
    os.makedirs(out, exist_ok=True)
    state = os.path.join(out, "bedroom.dst")
    if not os.path.exists(state):
        subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r); import battle_test; "
                        "battle_test.Game(%r).make_state(%r)" % (HERE, rom, state)], check=True)
    t = Tester(rom, tree, dump, out, state)
    failed = False
    checks = {"cliff_cave": t.check_cliff_cave, "contest": t.check_contest,
              "pokeathlon": lambda: check_pokeathlon(t), "supreme_cup": lambda: check_supreme_cup(t)}
    for name in [n for n in checks if not sys.argv[5:] or n in sys.argv[5:]]:
        ok, note = checks[name]()
        failed |= ok is False
        print("%-10s %s  %s" % (name, {True: "PASS", False: "FAIL", None: "SKIP"}[ok], note), flush=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
