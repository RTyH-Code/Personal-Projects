"""How the playtester decides what to press. No learning: rules plus randomness.

Overworld:
- Head for ground it hasn't stood on, preferring to keep going straight.
- When nothing new is next to it, walk (by the shortest known path) back
  to the nearest tile with an untried direction.
- When a map is used up, leave through a known exit, preferring the exits
  to maps it has seen least.
- When a step doesn't move it, press B once (to close any text) and try
  again; if it still doesn't move, the way is blocked. The first time it
  bumps into something, it presses A at it (people, signs, items, doors,
  HM obstacles).
- Now and then it opens the START menu and pokes around.

Battle: mostly A (fight), with some random menu moves so the bag, party and
RUN get used too. In wild battles it sometimes throws a Poké Ball.

Outside the overworld (title screen, text, menus): A and B.
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field

from .ram import GameState

DIRS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
REVERSE = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}


@dataclass
class Action:
    buttons: tuple[str, ...]
    hold: int = 8
    wait: int = 16
    tag: str = ""  # what it was for: move, interact, battle, menu, text, catch

    def to_json(self):
        return [list(self.buttons), self.hold, self.wait, self.tag]

    @classmethod
    def from_json(cls, a):
        return cls(tuple(a[0]), a[1], a[2], a[3])


@dataclass
class MapMemory:
    visited: set = field(default_factory=set)  # (x, y)
    blocked: set = field(default_factory=set)  # (x, y, dir)
    misses: dict = field(default_factory=dict)  # (x, y, dir) -> failed tries
    interacted: set = field(default_factory=set)  # (x, y, dir)
    exits: dict = field(default_factory=dict)  # (x, y, dir) -> map id it leads to

    def untried(self, x, y):
        out = []
        for d, (dx, dy) in DIRS.items():
            if (x, y, d) in self.blocked or (x, y, d) in self.exits:
                continue
            if (x + dx, y + dy) not in self.visited:
                out.append(d)
        return out


def tap(buttons, wait=20, tag=""):
    return Action(tuple(buttons), 6, wait, tag)


class Explorer:
    def __init__(self, rng: random.Random | None = None, map_visits=None, interact_prob=0.04, menu_prob=0.008,
                 catch_prob=0.35):
        self.rng = rng or random.Random()
        self.maps: dict[tuple[int, int], MapMemory] = {}
        self.map_visits = map_visits if map_visits is not None else {}  # map id -> visits (all workers)
        self.interact_prob = interact_prob
        self.menu_prob = menu_prob
        self.catch_prob = catch_prob
        self.queue: deque[Action] = deque()
        self.last_move = None  # (map, x, y, dir)
        self.retrying = False
        self.heading = self.rng.choice(list(DIRS))
        self.was_in_battle = False

    def mem(self, map_id) -> MapMemory:
        return self.maps.setdefault(map_id, MapMemory())

    # --- learning from the last step -----------------------------------------

    def _observe(self, s: GameState) -> None:
        if not s.valid:
            self.last_move = None
            return
        m = self.mem(s.map_id)
        m.visited.add((s.x, s.y))
        if self.last_move is None:
            return
        map_id, x, y, d = self.last_move
        self.last_move = None
        if s.in_battle:
            return  # a step that started a battle: judge it later
        if s.map_id != map_id:
            self.mem(map_id).exits[(x, y, d)] = s.map_id
            self.map_visits[s.map_id] = self.map_visits.get(s.map_id, 0) + 1
            self.retrying = False
            return
        if (s.x, s.y) != (x, y):
            self.retrying = False
            return
        key = (x, y, d)
        m.misses[key] = m.misses.get(key, 0) + 1
        if m.misses[key] >= 2:
            m.blocked.add(key)
            self.retrying = False
            if key not in m.interacted:
                m.interacted.add(key)
                self.queue.append(tap(("A",), 30, "interact"))
        else:
            # Maybe a text box was open: close it and try the same step again.
            self.retrying = True
            self.queue.append(tap(("B",), 20, "text"))
            self.queue.append(Action((d,), tag="move"))

    # --- choosing -------------------------------------------------------------

    def next(self, s: GameState) -> Action:
        self._observe(s)
        if self.queue:
            a = self.queue.popleft()
            if a.tag == "move" and s.valid:
                self.last_move = (s.map_id, s.x, s.y, a.buttons[0])
            return a
        if not s.valid:
            return tap(("A",) if self.rng.random() < 0.8 else ("START",), 30, "text")
        if s.in_battle:
            return self._battle(s)
        self.was_in_battle = False
        if self.rng.random() < self.menu_prob:
            self._menu_excursion()
            return self.queue.popleft()
        if self.rng.random() < self.interact_prob:
            return tap(("A",), 30, "interact")
        d = self._direction(s)
        if d is None:
            return tap((self.rng.choice(["A", "B"]),), 20, "text")
        self.heading = d
        self.last_move = (s.map_id, s.x, s.y, d)
        return Action((d,), tag="move")

    def _direction(self, s: GameState) -> str | None:
        m = self.mem(s.map_id)
        here = (s.x, s.y)
        options = m.untried(*here)
        if options:
            return self.heading if self.heading in options else self.rng.choice(options)
        path = self._path_to(m, here, lambda t: bool(m.untried(*t)))
        if path:
            return path[0]
        # This map is explored: head for an exit, least-visited destination first.
        exits = sorted(m.exits.items(), key=lambda e: (self.map_visits.get(e[1], 0), self.rng.random()))
        for (x, y, d), _dest in exits:
            if (x, y) == here:
                return d
            path = self._path_to(m, here, lambda t, x=x, y=y: t == (x, y))
            if path:
                return path[0]
        # Nothing known: forget a few walls (people move) and wander.
        if m.blocked and self.rng.random() < 0.2:
            m.blocked.discard(self.rng.choice(sorted(m.blocked)))
        return self.rng.choice(list(DIRS))

    def _path_to(self, m: MapMemory, start, goal) -> list[str] | None:
        """Shortest walk over known tiles to one matching `goal`, as directions."""
        if goal(start):
            return []
        prev = {start: None}
        q = deque([start])
        while q:
            t = q.popleft()
            for d, (dx, dy) in DIRS.items():
                n = (t[0] + dx, t[1] + dy)
                if n in prev or n not in m.visited or (t[0], t[1], d) in m.blocked:
                    continue
                prev[n] = (t, d)
                if goal(n):
                    path = []
                    while prev[n] is not None:
                        n, d2 = prev[n]
                        path.append(d2)
                    return path[::-1]
                q.append(n)
        return None

    def _battle(self, s: GameState) -> Action:
        if not self.was_in_battle:
            self.was_in_battle = True
            wild = not s.trainer_battle
            if wild and s.bag.get("poke_balls") and self.rng.random() < self.catch_prob:
                # From the opening message: BAG (right of FIGHT), the Poké Balls
                # pocket (two pockets right of Items), the first ball, USE.
                self.queue.extend([Action((), 0, 240, "catch"), tap(("A",), 200, "catch"), tap(("RIGHT",), 30, "catch"),
                                   tap(("A",), 150, "catch"), tap(("RIGHT",), 40, "catch"),
                                   tap(("RIGHT",), 40, "catch"), tap(("A",), 40, "catch"),
                                   tap(("A",), 400, "catch")])
                return self.queue.popleft()
        r = self.rng.random()
        if r < 0.78:
            b = "A"
        elif r < 0.84:
            b = "B"
        else:
            b = self.rng.choice(["UP", "DOWN", "LEFT", "RIGHT"])
        return tap((b,), 40, "battle")

    def _menu_excursion(self) -> None:
        """Open START and wander the menus a little, then back out."""
        self.queue.append(tap(("START",), 30, "menu"))
        for _ in range(self.rng.randint(1, 3)):
            self.queue.append(tap((self.rng.choice(["DOWN", "DOWN", "UP"]),), 15, "menu"))
        self.queue.append(tap(("A",), 60, "menu"))
        for _ in range(self.rng.randint(0, 6)):
            self.queue.append(tap((self.rng.choice(["UP", "DOWN", "LEFT", "RIGHT", "A", "B"]),), 25, "menu"))
        for _ in range(5):
            self.queue.append(tap(("B",), 30, "menu"))
