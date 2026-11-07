"""Walking anywhere in the game: the world map plus what the game state says.

World (world.py) knows the tiles. This adds what changes as you play:
- people standing in the way (each object, unless its hide flag is set:
  Snorlax after the Poké Flute, the Saffron Rockets after Silph Co....);
- Cut trees, Strength boulders and Rock Smash rocks: walls until the field
  move works (FireRed QoL + Hard: the HM in the bag and its badge), then
  obstacles to press A at;
- water: a wall until Surf works, then press A at it to start surfing;
- story gates (trigger tiles that turn you back) while their var says
  they're on, unless story.GATE_PASS says the script will let you through;
- the explorer's own memory of presses that didn't move it.

Plans are kept and followed while the player stays on them; leaving the
plan (a person in the way, a battle warp, a cutscene) makes a new one.
"""

from __future__ import annotations

from . import story
from .world import DIRS, WATER, World

HM_OBSTACLES = {
    "EventScript_CutTree": story.CAN_CUT,
    "EventScript_RockSmash": story.CAN_ROCK_SMASH,
    "EventScript_StrengthBoulder": story.CAN_STRENGTH,
}
OBSTACLE_TRIES = 3  # presses of A at one obstacle before it counts as a wall
FAIL_REST = 300  # after finding no way to a goal, wait this many presses before looking again


class Navigator:
    def __init__(self, world: World, game):
        self.world = world
        self.game = game
        self.id_by_name = {m["name"]: k for k, m in game.maps.items()}
        self.plan: list | None = None
        self.plan_key = None
        self.plan_at: dict = {}
        self.fail_until: dict = {}  # goal key -> press until which not to look again
        self.obstacle_tries: dict = {}  # (map, x, y) -> times it pressed A at that obstacle
        self._cache_key = None
        self._blocked = frozenset()
        self._obstacles: dict = {}

    def name(self, map_id) -> str:
        return self.game.map_name(*map_id)

    def knows(self, map_id) -> bool:
        return self.name(map_id) in self.world.maps

    # --- what's in the way now -------------------------------------------------

    def _flag_set(self, flag_name: str, s, here: str, on: str) -> bool:
        """Whether an object's hide flag is set. Temporary flags clear when a map loads,
        so off the map they're clear."""
        if not flag_name or flag_name == "0":
            return False
        if flag_name.startswith("FLAG_TEMP_") and on != here:
            return False
        try:
            n = int(flag_name, 0)
        except ValueError:
            n = self.game.flags.get(flag_name.removeprefix("FLAG_"))
        return n is not None and bool(s.flag(n))

    def gate_active(self, trig, s, here: str, on: str) -> bool:
        x, y, var_name, value, script, gate = trig
        if not gate or not var_name or story.gate_passable(script, s, self.game):
            return False
        try:
            want = int(value, 0)
        except ValueError:
            return False
        if not story.gate_var_is_live(var_name) and on != here:
            return want == 0  # reset when the map loads: on, if it waits for 0
        n = self.game.vars.get(var_name.removeprefix("VAR_"))
        return n is not None and s.var(n) == want

    def obstacles(self, s) -> tuple[frozenset, dict]:
        """(blocked tiles, HM obstacles that can be cleared now: tile -> what)."""
        here = self.name(s.map_id)
        key = (bytes(s.flags or b""), bytes(getattr(s, "vars", b"") or b""), here)
        if key == self._cache_key:
            return self._blocked, self._obstacles
        blocked, obstacles = set(), {}
        for name, m in self.world.maps.items():
            for o in m.objects:
                lid, x, y, script, hide = o
                if lid:
                    x, y = story.placed(name, lid, x, y, s, self.game)
                if self._flag_set(hide, s, here, name) or (x, y) in m.warp_at:
                    continue  # gone, or a cutscene's actor waiting on a doorway
                can = HM_OBSTACLES.get(script)
                if can is not None and can(s, self.game):
                    obstacles[(name, x, y)] = script
                    continue
                blocked.add((name, x, y))
            for t in m.triggers:
                if len(t) >= 6 and self.gate_active(t, s, here, name):
                    blocked.add((name, t[0], t[1]))
        self._cache_key = key
        self._blocked, self._obstacles = frozenset(blocked), obstacles
        return self._blocked, self._obstacles

    # --- planning and following -------------------------------------------------

    def step(self, s, key, goal, t: int, avoid=frozenset()) -> tuple[str, str] | None:
        """What to press to get one step nearer a tile where goal(map, x, y) holds:
        ("move", dir), ("use", dir) to press A at an obstacle or water in that
        direction, or None if already there or there's no known way. `key`
        names the goal (plans are kept per goal). `avoid`: presses known not to
        work, (map, x, y, dir), or a function giving them (called only to plan)."""
        if not self.knows(s.map_id):
            return None
        here = (self.name(s.map_id), s.x, s.y)
        if goal(*here):
            return None
        if self.fail_until.get(key, -1) > t:
            return None
        if self.plan_key != key or here not in self.plan_at:
            self._make_plan(s, key, goal, avoid)
            if self.plan is None:
                self.fail_until[key] = t + FAIL_REST
                return None
        _m, x, y, d = self.plan[self.plan_at[here]]
        target = self._next_tile(here, d)
        if target is not None and self._needs_use(s, here, target):
            tries = self.obstacle_tries.get(target, 0)
            if tries < OBSTACLE_TRIES:
                self.obstacle_tries[target] = tries + 1
                self.plan_key = None  # look again once it's cleared
                return "use", d
        return "move", d

    def _next_tile(self, here, d):
        dx, dy = DIRS[d]
        return here[0], here[1] + dx, here[2] + dy

    def _needs_use(self, s, here, target) -> bool:
        _blocked, obstacles = self.obstacles(s)
        if target in obstacles:
            return True
        m = self.world.maps.get(here[0])
        c, c0 = m.cell(target[1], target[2]), m.cell(here[1], here[2])
        return c is not None and c0 is not None and bool(c & WATER) and not c0 & WATER

    def _make_plan(self, s, key, goal, avoid) -> None:
        if callable(avoid):
            avoid = avoid()
        blocked, obstacles = self.obstacles(s)
        tried_out = {k for k, n in self.obstacle_tries.items() if n >= OBSTACLE_TRIES}
        here = (self.name(s.map_id), s.x, s.y)
        surf = story.CAN_SURF(s, self.game)
        # Don't avoid the presses into an obstacle we can clear: they failed because it was there.
        avoid = {a for a in avoid if self._next_tile(a[:3], a[3]) not in obstacles
                 or self._next_tile(a[:3], a[3]) in tried_out}
        plan = self.world.route(here, goal, surf=surf, avoid=avoid, blocked=blocked | tried_out)
        self.plan, self.plan_key = plan, key
        self.plan_at = {p[:3]: i for i, p in enumerate(plan or [])}

    def avoid_from(self, memories) -> set:
        """The explorer's blocked presses ({map id: MapMemory}) as (map, x, y, dir)."""
        out = set()
        for map_id, mem in memories.items():
            name = self.name(map_id)
            out.update((name, x, y, d) for x, y, d in mem.blocked)
        return out

    # --- goals --------------------------------------------------------------------

    def talk_spots(self, s, map_name: str, parts) -> list[list[tuple[int, int, str]]]:
        """For each person or sign on `map_name` whose script contains one of `parts`
        (people only while they're there): the tiles to stand on to talk to them, facing."""
        m = self.world.maps.get(map_name)
        if m is None:
            return []
        here = self.name(s.map_id)
        out = []
        for part in parts:
            for o in m.objects:
                if part in o[3] and not self._flag_set(o[4], s, here, map_name):
                    out.append(self.world.adjacent_spots(map_name, o[1], o[2]))
            for sign in m.signs:
                if part in sign[3]:
                    out.append(self.world.adjacent_spots(map_name, sign[0], sign[1]))
        return [spots for spots in out if spots]

    def trigger_tiles(self, map_name: str, parts) -> set:
        m = self.world.maps.get(map_name)
        if m is None:
            return set()
        return {(t[0], t[1]) for t in m.triggers if any(p in t[4] for p in parts)}

    def nurse_spots(self) -> dict:
        """Where to stand to talk to each Pokémon Center nurse: {(map, x, y): facing}."""
        out = {}
        for name, m in self.world.maps.items():
            for o in m.objects:
                if o[3].endswith("EventScript_Nurse"):
                    for x, y, d in self.world.adjacent_spots(name, o[1], o[2]):
                        out[(name, x, y)] = d
        return out
