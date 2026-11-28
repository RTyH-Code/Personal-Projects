#!/usr/bin/env python3
"""Check the field moves the hack lets a player use without teaching them (patch 0007), in the emulator.

    hm_test.py TEST_ROM TREE DUMP OUT [MOVE ...]

TEST_ROM, TREE and DUMP are as for walk_test.py (a build with the test harness). The party knows nothing but
Tackle. Each of Rock Smash, Cut, Strength, Surf, Whirlpool, Waterfall and Rock Climb is tried three times,
facing its obstacle and pressing A:

- with the HM in the bag and the badge that the game asks for: "use it?" is asked, and after Yes the rock or
  tree is gone, the boulder moves, or the player is on, through or up the water or the rock wall;
- with the HM but one badge short of it (the harness gives badges in the game's order): nothing is asked;
- with the badge but no HM: nothing is asked.

Moves named after OUT (such as Surf, or Rock_Smash) limit it to those. Prints PASS or FAIL for each try, and screenshots of the failures in OUT.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import battle_test
import story_bot
from walk_test import DIRS, WATER

WHIRLPOOL, WATERFALL, ROCK_CLIMB = story_bot.WHIRLPOOL, story_bot.WATERFALL, story_bot.ROCK_CLIMB

# (move, HM, badges needed: the game gives them in order, so the one checked is the last of these, and the
# script command that checks it), what stands in the way
CASES = [
    ("Rock Smash", "HM06", 1, ("object", "std_field_rock_smash")),        # Zephyr Badge
    ("Cut", "HM01", 2, ("object", "std_field_cut")),                      # Hive Badge
    ("Strength", "HM04", 3, ("object", "std_field_strength")),            # Plain Badge
    ("Surf", "HM03", 4, ("water", None)),                                 # Fog Badge
    ("Whirlpool", "HM05", 7, ("water", WHIRLPOOL)),                       # Glacier Badge
    ("Waterfall", "HM07", 8, ("water", WATERFALL)),                       # Rising Badge
    ("Rock Climb", "HM08", 16, ("land", ROCK_CLIMB)),                     # Earth Badge
]
# maps to try first (ordinary routes, away from story scenes); any other map with the obstacle comes after
PREFERRED = ["R41", "D46R0101", "R32", "R36", "R29", "R43", "R42", "R44", "R45", "R46", "R27", "R26", "W41", "R40", "R41", "D35R0102",
             "R09", "R03", "R02"]


def tackle_only(real):
    """reference_party, with every Pokemon knowing only Tackle, so no field move is known by anyone."""
    def party(data, level):
        moves = data["boss_teams"].MOVE_IDS
        tackle = moves.get("TACKLE", moves.get("MOVE_TACKLE"))
        return [(a, species, c, [tackle], item) for a, species, c, _, item in real(data, level)]
    return party


def raw_grid(world, name):
    """{(x, z): (behaviour, blocked)} of a map's own tiles, the blocked ones included."""
    grid, owner = world.grid(world.headers[name]["matrix"])
    mine = world.map_ids[name]
    own = {p: v for p, v in grid.items() if not owner or owner.get(p) == mine}
    return {p: (v & 0xFF, bool(v & 0x8000)) for p, v in (own or grid).items()}


def ordered(names):
    first = [n for n in PREFERRED if n in names]
    return first + sorted(n for n in names if n not in first)


def spots(world, kind, what):
    """Places to try a field move, best first: (map, where to stand, direction to face, object id or None, tiles to
    surf on before the obstacle after the first)."""
    found = []
    names = [n for n in world.headers if n in world.map_ids]
    for name in ordered(names):
        try:
            grid = raw_grid(world, name)
            events = world.events(name)
        except Exception:
            continue
        occupied = {(e["x"], e["z"]) for k in ("object_events", "warp_events", "bg_events", "coord_events")
                    for e in events.get(k, [])}
        ground = lambda p: p in grid and not grid[p][1] and grid[p][0] not in WATER and p not in occupied
        water = lambda p: p in grid and not grid[p][1] and grid[p][0] in WATER and p not in occupied
        if kind == "object":
            for i, e in enumerate(events.get("object_events", [])):
                if str(e.get("script")) != what:
                    continue
                for d, (dx, dz, _) in DIRS.items():
                    stand, beyond = (e["x"] - dx, e["z"] - dz), (e["x"] + dx, e["z"] + dz)
                    # a boulder needs somewhere to be pushed to
                    if ground(stand) and (what != "std_field_strength" or ground(beyond)):
                        found.append((name, stand, d, i, 0))
                        break
        elif name[0] in "RW" or name.startswith("D41R01"):     # outside (indoors the same values mean other things)
            for p in sorted(grid):
                if not ground(p):
                    continue
                for d, (dx, dz, _) in DIRS.items():
                    a, b = (p[0] + dx, p[1] + dz), (p[0] + 2 * dx, p[1] + 2 * dz)
                    if kind == "land" and grid.get(a, (None,))[0] == what:
                        found.append((name, p, d, None, 0))
                    elif kind == "water" and what is None and water(a) and water(b):
                        found.append((name, p, d, None, 0))
                    elif kind == "water" and what is not None and water(a) and (what != WATERFALL or d == "up"):
                        # out over up to six tiles of water, straight on, to the whirlpool or the waterfall
                        far = None
                        for k in range(1, 8):
                            q = (p[0] + k * dx, p[1] + k * dz)
                            if grid.get(q, (None,))[0] == what:
                                far = k
                                break
                            if not water(q):
                                break
                        if far is None or far < 2:
                            continue
                        found.append((name, p, d, None, far - 2))
                    else:
                        continue
                    break
                if found and found[-1][0] == name:
                    break       # one place per map is enough
        if len(found) >= 6:
            break
    return found


class Tester:
    def __init__(self, rom, tree, dump, out, state):
        battle_test.reference_party = tackle_only(battle_test.reference_party)
        self.bot = story_bot.Bot(rom, tree, dump, out)
        self.g, self.world, self.data = self.bot.game, self.bot.world, self.bot.data
        self.state, self.out = state, out

    def place(self, name, stand, d, items, badges, hidden):
        p = self.g.start(self.state, self.data, self.world, name, stand, facing=DIRS[d][2], badges=badges,
                         items=[self.data["items"][i] for i in items], clear_flags=hidden,
                         flags=["FLAG_GAME_CLEAR"])
        if p is None:
            return False
        self.bot.fs = None
        for hold in (2, 4, 8):
            self.g.key(d, hold=hold, after=10)
            if self.bot.facing() == d:
                break
        return self.bot.facing() == d

    def question(self):
        """The Yes/No buttons, which span the touch screen, under a message. (story_bot's check looks at their right
        ends only, and the field's touch screen has a pale panel there when it shows few badges.)"""
        image = self.g.emu.screenshot()
        light = lambda x, y: min(image.getpixel((x, y))[:3]) > 150
        return (self.bot.question() and light(40, 192 + 72) and light(40, 192 + 120)
                and story_bot.text_box(image))

    def ask(self):
        """A, and through any messages: True if a yes/no question came up (it is answered Yes)."""
        self.g.key("a", after=30)
        for _ in range(16):
            if self.question():
                self.bot.settle(["a"])
                return True
            if not story_bot.text_box(self.g.emu.screenshot()):
                self.g.run(20)
                if not story_bot.text_box(self.g.emu.screenshot()):
                    return False
            self.g.key("a", after=30)
            self.g.run_every_frame(20)
        return False

    def surf(self, d):
        """From the shore, onto the water ahead (with HM03 and the Fog Badge, which every water case has)."""
        before = self.g.position()
        if not self.ask():
            return False
        self.bot.settle()
        p = self.g.position()
        return bool(p and before and p[1:3] != before[1:3])

    def attempt(self, case, spot, items, badges):
        """(asked, done, note) for one try; (None, None, why) if it couldn't be made."""
        try:
            return self._attempt(case, spot, items, badges)
        except story_bot.Stuck as e:
            return None, None, "stuck: %s" % e

    def _attempt(self, case, spot, items, badges):
        move, hm, need, (kind, what) = case
        name, stand, d, obj, further = spot
        events = self.world.events(name).get("object_events", [])
        hidden = sorted({e["hidden_flag"] for e in events if str(e.get("script", "")).startswith("std_field")
                         and e.get("hidden_flag") in self.world.flags})
        if not self.place(name, stand, d, items, badges, hidden):
            return None, None, "the harness did not put the player at %s %s facing %s" % (name, stand, d)
        if kind == "water" and what is not None:
            if not self.surf(d):
                return None, None, "could not surf out from %s %s" % (name, stand)
            for _ in range(further):
                self.g.step(d)
            self.bot.settle()
        start = self.g.position()
        objects = self.bot.objects()
        if obj is not None and obj not in objects:
            return None, None, "object %d is not on %s" % (obj, name)
        asked = self.ask()
        self.bot.settle()
        if move == "Strength" and asked:
            self.g.key(d, hold=24, after=60)        # push it
            self.bot.settle()
        p, now = self.g.position(), self.bot.objects()
        if obj is not None and move != "Strength":
            done = obj not in now
        elif obj is not None:
            done = now.get(obj) != objects[obj]
        else:
            done = bool(p and start and p[1:3] != start[1:3])
        return asked, done, "at %s %s" % (name, stand)

    def run(self, only=()):
        results = []
        for case in [c for c in CASES if not only or c[0].replace(" ", "_") in only or c[0] in only]:
            move, hm, need, (kind, what) = case
            candidates = spots(self.world, kind, what)
            if not candidates:
                print("%-10s %-20s FAIL  nowhere found to try it" % (move, "HM and badge"), flush=True)
                results.append((move, "everything", False, "nowhere found to try it"))
                continue
            items = [hm] if move == "Surf" or kind != "water" else [hm, "HM03"]
            no_hm = [] if move == "Surf" or kind != "water" else ["HM03"]
            # find a place where the full try works; then try the same place without the badge, and without the HM
            used, note = None, ""
            for spot in candidates:
                asked, done, note = self.attempt(case, spot, items, need)
                if asked and done:
                    used = spot
                    break
                self.g.emu.screenshot().save(os.path.join(self.out, "%s_%s.png" % (move.replace(" ", "_"), spot[0])))
                note = "asked %s, done %s %s" % (asked, done, note)
            ok = used is not None
            print("%-10s %-20s %s  %s" % (move, "HM and badge", "PASS" if ok else "FAIL", note), flush=True)
            results.append((move, "HM and badge", ok, note))
            if not ok:
                continue
            for label, its, badges in (("one badge short", items, need - 1), ("no HM", no_hm, need)):
                if move == "Surf" and label == "no HM":
                    its = []
                asked, done, note = self.attempt(case, used, its, badges)
                ok = asked is False and not done
                if not ok:
                    self.g.emu.screenshot().save(os.path.join(self.out, "%s_%s.png" % (move.replace(" ", "_"),
                                                                                       label.replace(" ", "_"))))
                print("%-10s %-20s %s  asked %s, done %s %s" % (move, label, "PASS" if ok else "FAIL", asked, done,
                                                                note), flush=True)
                results.append((move, label, ok, note))
        return results


def main():
    rom, tree, dump, out = sys.argv[1:5]
    os.makedirs(out, exist_ok=True)
    state = os.path.join(out, "bedroom.dst")
    if not os.path.exists(state):
        # making the state and then a Walker in one process can crash the emulator: make it in its own
        import subprocess
        subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r); import battle_test; "
                        "battle_test.Game(%r).make_state(%r)" % (HERE, rom, state)], check=True)
    results = Tester(rom, tree, dump, out, state).run(sys.argv[5:])
    sys.exit(0 if all(ok for _, _, ok, _ in results) else 1)


if __name__ == "__main__":
    main()
