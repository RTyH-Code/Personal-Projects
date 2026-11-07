"""How the playtester decides what to press. No learning: rules plus randomness.

Overworld:
- Head for ground it hasn't stood on, preferring to keep going straight.
- When nothing new is next to it, walk (by the shortest known path) back
  to the nearest tile with an untried direction.
- When a map is used up, leave through a known exit, preferring the exits
  to maps it has seen least.
- When a step doesn't move it, press B once (to close any text) and try
  again; if it still doesn't move, the way is blocked. Walls are forgotten
  at the start of each session and when the story moves on, because some
  are scripts (Oak stopping you leaving Pallet Town) that go away later. The first time it
  bumps into something, it presses A at it (people, signs, items, doors,
  HM obstacles).
- Now and then it opens the START menu and pokes around.

Healing: when the party is healed right after it talks to someone (Mom, a
Pokémon Center nurse), it remembers that spot. When the party's HP drops
below 40%, or its attacks are out of PP, it walks back there through the
maps it knows and talks again.

Battle (with a game profile): FIGHT and the move that does the most damage
against the opponent (power, same-type bonus, type chart, accuracy). When
one of ours faints, send in the next that can fight. Run from wild battles
below half HP; sometimes throw a Poké Ball; now and then a random press so
other battle menus get used. After a level-up, no B for a while (it would
cancel an evolution).

Training: when the strongest Pokémon is more than TRAIN_MARGIN levels under
the next Gym Leader's strongest, and healthy, walk in grass where wild
battles have started before.

Errands: holding a story item (Oak's Parcel, the S.S. Ticket...), head for
the map that needs it (ERRANDS), through exits it knows.

Outside the overworld (title screen, text, menus): A and B.
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field

from .ram import GameState

DIRS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
FORGET_EVERY = 200  # at most this often, forget walls when the story flags change
HEAL_BELOW = 0.4  # go back to a known healing spot when the party's HP is below this
RUN_BELOW = 0.5  # run from wild battles when the party's HP is below this
HEAL_SEEN_WITHIN = 15  # a full heal this many presses after talking to someone: they heal
TRAIN_MARGIN = 2  # train until the strongest Pokémon is this close to the next Gym Leader's level
TRAIN_HP = 0.6  # only go training with at least this much HP
TRAIN_SHARE = 0.6  # share of overworld presses spent training (the rest keep exploring)
ERRAND_SHARE = 0.6  # share of overworld presses spent heading for an errand's destination
ERRAND_STEPS = 400  # presses to spend at an errand's destination before it counts as tried
NO_B_AFTER_LEVEL_UP = 80  # presses without B after a battle with a level-up (B cancels evolution)

# FireRed's item-gated story: holding the item, go to one of these maps.
ERRANDS = [
    ("OAKS_PARCEL", ["PalletTown_ProfessorOaksLab"]),
    ("SS_TICKET", ["VermilionCity", "SSAnne_Exterior"]),
    ("BIKE_VOUCHER", ["CeruleanCity_BikeShop"]),
    ("TEA", ["Route5_SouthEntrance", "Route6_NorthEntrance", "Route7_EastEntrance", "Route8_WestEntrance"]),
    ("SILPH_SCOPE", ["PokemonTower_6F", "PokemonTower_7F"]),
    ("POKE_FLUTE", ["Route12", "Route16"]),
    ("GOLD_TEETH", ["FuchsiaCity_WardensHouse"]),
    ("LIFT_KEY", ["RocketHideout_Elevator", "RocketHideout_B4F"]),
    ("CARD_KEY", ["SilphCo_5F", "SilphCo_7F", "SilphCo_9F", "SilphCo_11F"]),
    ("SECRET_KEY", ["CinnabarIsland_Gym"]),
]
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
                 catch_prob=0.35, game=None):
        self.rng = rng or random.Random()
        self.game = game  # the game profile: moves, types, gym levels, items (optional)
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
        self.flags_seen = None
        self.steps_since_forget = 0
        self.t = 0  # presses so far
        # Healing: where talking to someone healed the party (Mom, a Pokémon Center
        # nurse), per map: (x, y, facing). Learned by noticing it happen.
        self.heal_spots: dict[tuple[int, int], tuple[int, int, str]] = {}
        self.heal_fails: dict[tuple[int, int], int] = {}
        self.last_talk = None  # (map, x, y, facing, press)
        self.prev_hp = None
        self.prev_party = 0
        self.heal_attempt = None  # press when it last talked at a healing spot
        self.run_cooldown = 0
        self.grass: dict[tuple[int, int], set] = {}  # map -> tiles where wild battles started
        self.errand_steps: dict[str, int] = {}
        self.no_b_until = 0
        self.battle_levels = None  # party levels when the current battle started
        self.fainted_seen = 0

    def new_session(self) -> None:
        """Forget walls (keep layouts and exits): the next start may be further into the game."""
        self.forget_walls()
        self.queue.clear()
        self.last_move = None
        self.retrying = False
        self.was_in_battle = False
        self.errand_steps.clear()

    def forget_walls(self) -> None:
        """Some walls are scripts that stop the player (Oak at the edge of Pallet Town)
        and go away as the story moves on, so they shouldn't be remembered forever."""
        for m in self.maps.values():
            m.blocked.clear()
            m.misses.clear()
            m.interacted.clear()
        self.steps_since_forget = 0

    def mem(self, map_id) -> MapMemory:
        return self.maps.setdefault(map_id, MapMemory())

    # --- learning from the last step -----------------------------------------

    def _close_button(self) -> str:
        """B closes text and menus, but cancels an evolution: right after a level-up, use A."""
        return "A" if self.t < self.no_b_until else "B"

    def _talk(self, map_id, x, y, facing) -> None:
        """Press A at what's in front, then A a few more times: that reads the text and
        answers YES (a nurse asks "Shall I heal?"; B would mean no)."""
        self.last_talk = (map_id, x, y, facing, self.t)
        self.queue.append(tap(("A",), 30, "interact"))
        for _ in range(3):
            self.queue.append(tap(("A",), 40, "talk"))

    def _learn_healing(self, s: GameState) -> None:
        """Notice the party being healed right after talking to someone, and remember where."""
        live = [mon for mon in s.party if not mon.is_egg]
        hp = s.hp_fraction if live else None
        talk = self.last_talk
        if (hp is not None and self.prev_hp is not None and not s.in_battle and talk is not None
                and self.prev_hp < 0.95 and hp >= 0.999 and len(s.party) == self.prev_party
                and talk[0] == s.map_id and self.t - talk[4] <= HEAL_SEEN_WITHIN):
            self.heal_spots[s.map_id] = talk[1:4]
            self.heal_fails.pop(s.map_id, None)
        self.prev_hp = hp
        self.prev_party = len(s.party)

    def _observe(self, s: GameState) -> None:
        if not s.valid:
            self.last_move = None
            return
        self._learn_healing(s)
        m = self.mem(s.map_id)
        m.visited.add((s.x, s.y))
        if self.last_move is None:
            return
        map_id, x, y, d = self.last_move
        self.last_move = None
        if s.in_battle:
            if not s.trainer_battle and s.map_id == map_id:
                self.grass.setdefault(s.map_id, set()).add((s.x, s.y))  # a wild battle: grass (or water, a cave)
            return
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
            if all((x, y, dd) in m.blocked for dd in DIRS):
                # Walled in on all sides: really a screen that swallows the d-pad (the
                # nickname screen, a menu). START jumps to OK on the naming screen.
                for dd in DIRS:
                    m.blocked.discard((x, y, dd))
                self.queue.extend([tap(("START",), 40, "escape"), tap(("A",), 60, "escape")])
                self.queue.extend([tap((self._close_button(),), 30, "escape") for _ in range(4)])
            elif key not in m.interacted:
                m.interacted.add(key)
                self._talk(s.map_id, x, y, d)
        else:
            # Maybe a text box was open: close it and try the same step again.
            self.retrying = True
            self.queue.append(tap((self._close_button(),), 20, "text"))
            self.queue.append(Action((d,), tag="move"))

    # --- choosing -------------------------------------------------------------

    def next(self, s: GameState) -> Action:
        self.t += 1
        self._observe(s)
        self.steps_since_forget += 1
        if s.valid and s.flags:
            # The story moved on (an event, a badge, a gift...): paths may have opened.
            if self.flags_seen is not None and s.flags != self.flags_seen and self.steps_since_forget >= FORGET_EVERY:
                self.forget_walls()
            self.flags_seen = s.flags
        if self.queue:
            a = self.queue.popleft()
            if a.tag == "move" and s.valid:
                self.last_move = (s.map_id, s.x, s.y, a.buttons[0])
            return a
        if not s.valid:
            return tap(("A",) if self.rng.random() < 0.8 else ("START",), 30, "text")
        if s.in_battle:
            return self._battle(s)
        if self.was_in_battle and self.battle_levels is not None:
            if [m.level for m in s.party] > self.battle_levels:  # leveled up: an evolution may follow
                self.no_b_until = self.t + NO_B_AFTER_LEVEL_UP
        self.was_in_battle = False
        self.battle_levels = None
        if self.rng.random() < self.menu_prob and self.t >= self.no_b_until:
            self._menu_excursion()
            return self.queue.popleft()
        if self._needs_healing(s):
            a = self._go_heal(s)
            if a is not None:
                return a
        a = self._errand(s)
        if a is not None:
            return a
        if self._wants_training(s) and self.rng.random() < TRAIN_SHARE:
            a = self._train(s)
            if a is not None:
                return a
        if self.rng.random() < self.interact_prob:
            self.last_talk = (s.map_id, s.x, s.y, self.heading, self.t)
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
        # This map looks explored. Now and then, try a wall again (it may have
        # been a person, or a script that has since gone) rather than an exit.
        if m.blocked and self.rng.random() < 0.25:
            m.blocked.discard(self.rng.choice(sorted(m.blocked)))
            path = self._path_to(m, here, lambda t: bool(m.untried(*t)))
            if path is not None:
                return path[0] if path else self._direction(s)
        # Head for an exit, least-visited destination first.
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

    # --- healing ----------------------------------------------------------------

    def _needs_healing(self, s: GameState) -> bool:
        live = [mon for mon in s.party if not mon.is_egg and mon.hp > 0]
        if not live or not self.heal_spots:
            return False
        out_of_pp = self.game is not None and not any(self.game.has_damaging_pp(mon) for mon in live)
        return s.hp_fraction < HEAL_BELOW or out_of_pp

    def _map_route(self, start, goals) -> list | None:
        """Maps to walk through (by known exits) to reach one of `goals`."""
        prev = {start: None}
        q = deque([start])
        while q:
            cur = q.popleft()
            if cur in goals:
                route = []
                while cur is not None:
                    route.append(cur)
                    cur = prev[cur]
                return route[::-1]
            for dest in set(self.mem(cur).exits.values()):
                if dest not in prev:
                    prev[dest] = cur
                    q.append(dest)
        return None

    def _travel(self, s: GameState, goal_maps: set) -> Action | None:
        """One step towards the nearest of `goal_maps`, through exits it knows. None if there's
        no known way, or it's already there."""
        route = self._map_route(s.map_id, goal_maps)
        if route is None or len(route) == 1:
            return None
        m = self.mem(s.map_id)
        here = (s.x, s.y)
        doors = [(ex, ey, d) for (ex, ey, d), dest in m.exits.items() if dest == route[1]]
        for ex, ey, d in doors:
            if (ex, ey) == here:
                self.last_move = (s.map_id, s.x, s.y, d)
                return Action((d,), tag="move")
        for ex, ey, _d in doors:
            path = self._path_to(m, here, lambda t, ex=ex, ey=ey: t == (ex, ey))
            if path:
                self.last_move = (s.map_id, s.x, s.y, path[0])
                return Action((path[0],), tag="move")
        return None

    # --- errands and training ----------------------------------------------------

    def _errand(self, s: GameState) -> Action | None:
        """Holding a story item (Oak's Parcel, the S.S. Ticket...): head for where it's needed."""
        if self.game is None:
            return None
        for item, places in ERRANDS:
            num = self.game.item(item)
            if num is None or s.item_count(num) == 0 or self.errand_steps.get(item, 0) >= ERRAND_STEPS:
                continue
            goals = {k for k, m in self.game.maps.items() if m["name"] in places}
            if s.map_id in goals:
                self.errand_steps[item] = self.errand_steps.get(item, 0) + 1
                return None  # there: explore and talk as usual
            if self.rng.random() < ERRAND_SHARE:
                return self._travel(s, goals)
            return None
        return None

    def _wants_training(self, s: GameState) -> bool:
        if self.game is None or not self.grass:
            return False
        live = [mon for mon in s.party if not mon.is_egg]
        if not live or s.hp_fraction < TRAIN_HP:
            return False
        top = max(mon.level for mon in live)
        return top < self.game.next_gym_level(s) - TRAIN_MARGIN

    def _train(self, s: GameState) -> Action | None:
        """Walk in grass it knows (where wild battles started) to win some battles."""
        grass = self.grass.get(s.map_id)
        if not grass:
            return self._travel(s, set(self.grass))
        m = self.mem(s.map_id)
        here = (s.x, s.y)
        if here in grass:
            # Pace about in the grass.
            options = [d for d, (dx, dy) in DIRS.items()
                       if (here[0] + dx, here[1] + dy) in grass and (here[0], here[1], d) not in m.blocked]
            if not options:
                options = [d for d in DIRS if (here[0], here[1], d) not in m.blocked]
            d = self.rng.choice(options or list(DIRS))
        else:
            path = self._path_to(m, here, lambda t: t in grass)
            if not path:
                return None
            d = path[0]
        self.last_move = (s.map_id, s.x, s.y, d)
        return Action((d,), tag="move")

    def _go_heal(self, s: GameState) -> Action | None:
        """One step towards the nearest known healing spot, or talk to it once there."""
        route = self._map_route(s.map_id, set(self.heal_spots))
        if route is None:
            return None
        m = self.mem(s.map_id)
        here = (s.x, s.y)
        if len(route) == 1:
            x, y, facing = self.heal_spots[s.map_id]
            if here == (x, y):
                if self.heal_attempt is not None and self.t - self.heal_attempt < 40:
                    return None  # just tried: let the result show before trying again
                if self.heal_attempt is not None:
                    # Talked here before and still hurt: after a few tries, forget the spot.
                    self.heal_fails[s.map_id] = self.heal_fails.get(s.map_id, 0) + 1
                    if self.heal_fails[s.map_id] >= 3:
                        del self.heal_spots[s.map_id]
                        self.heal_attempt = None
                        return None
                self.heal_attempt = self.t
                self._talk(s.map_id, x, y, facing)
                return tap((facing,), 10, "heal")  # face them first
            path = self._path_to(m, here, lambda t: t == (x, y))
        else:
            return self._travel(s, set(self.heal_spots))
        if not path:
            return None
        self.last_move = (s.map_id, s.x, s.y, path[0])
        return Action((path[0],), tag="move")

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
        wild = not s.trainer_battle
        live = [mon for mon in s.party if not mon.is_egg]
        fainted = sum(1 for mon in live if mon.hp == 0)
        alive = [i for i, mon in enumerate(s.party) if not mon.is_egg and mon.hp > 0]
        first_step = not self.was_in_battle
        self.was_in_battle = True
        if first_step:
            self.fainted_seen = fainted
            self.battle_levels = [mon.level for mon in s.party]
        elif fainted > self.fainted_seen and alive:
            # One of ours fainted: the game asks to send in the next. YES, then pick the
            # first that can fight (the party menu lists them top to bottom), SHIFT.
            self.fainted_seen = fainted
            self.queue.append(tap(("A",), 60, "switch"))
            self.queue.extend(tap(("DOWN",), 20, "switch") for _ in range(alive[0]))
            self.queue.extend([tap(("A",), 40, "switch"), tap(("A",), 90, "switch")])
            return self.queue.popleft()
        self.run_cooldown -= 1
        if wild and live and s.hp_fraction < RUN_BELOW and self.run_cooldown <= 0:
            # RUN: back out to the action menu (FIGHT BAG / POKéMON RUN), then down, right, A.
            self.run_cooldown = 12
            self.queue.extend([tap(("B",), 30, "run"), tap(("B",), 30, "run"), tap(("DOWN",), 20, "run"),
                               tap(("RIGHT",), 20, "run"), tap(("A",), 90, "run"), tap(("A",), 60, "run")])
            return self.queue.popleft()
        if first_step and wild and s.bag.get("poke_balls") and self.rng.random() < self.catch_prob:
            # From the opening message: BAG (right of FIGHT), the Poké Balls
            # pocket (two pockets right of Items), the first ball, USE.
            self.queue.extend([Action((), 0, 240, "catch"), tap(("A",), 200, "catch"), tap(("RIGHT",), 30, "catch"),
                               tap(("A",), 150, "catch"), tap(("RIGHT",), 40, "catch"),
                               tap(("RIGHT",), 40, "catch"), tap(("A",), 40, "catch"),
                               tap(("A",), 400, "catch")])
            return self.queue.popleft()
        if self.game is not None and self.rng.random() < 0.85:
            return self._fight(s)
        # Some random presses, so the bag, party and summary screens get used too.
        b = "A" if self.rng.random() < 0.7 else self.rng.choice(["UP", "DOWN", "LEFT", "RIGHT"])
        return tap((b,), 40, "battle")

    def _fight(self, s: GameState) -> Action:
        """FIGHT, then the best move. The cursors remember where they were, so first push
        them to the top left (FIGHT; the first move) and go from there."""
        mon, foe = s.active, s.active_enemy
        slot = self.game.best_move(mon, foe) if mon is not None else 0
        seq = [tap(("UP",), 15, "fight"), tap(("LEFT",), 15, "fight"), tap(("A",), 40, "fight"),
               tap(("UP",), 15, "fight"), tap(("LEFT",), 15, "fight")]
        if slot in (1, 3):
            seq.append(tap(("RIGHT",), 15, "fight"))
        if slot in (2, 3):
            seq.append(tap(("DOWN",), 15, "fight"))
        seq += [tap(("A",), 120, "fight"), tap(("A",), 60, "fight"), tap(("A",), 60, "fight")]
        self.queue.extend(seq[1:])
        return seq[0]

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
