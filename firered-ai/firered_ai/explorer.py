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
the next Gym Leader's strongest, and healthy: with the world map, challenge
the nearest trainer still to beat (not far stronger than the team), outside
gyms first, then the next gym's; when none are left, walk in the last grass
on the way to the next checklist item (wild Pokémon are stronger there).
Without the world map, walk in grass where wild battles have started before.
At a gym, its trainers come before the leader.

The checklist (with the world map): nearly all the time, work on the first
checklist item not yet done (checklist.py: the story's objectives, with the
hack's features to try slotted in): walk there by the shortest way the world
map knows (navigate.py), talk to the people or step on the tiles it names,
and press A at Cut trees, rocks and water on the way. After trying a hack
feature it waits to see it work (a flag, an item, a battle starting); one
that doesn't after a few tries is reported. An item not done after
STORY_BUDGET presses (CHECK_BUDGET for hack checks) is put aside for a while,
so a stuck tester looks around instead of walking into the same wall.
Exploring on its own is only for when nothing on the list can be reached.
With the world map, healing goes to the nearest Pokémon Center and training
to the nearest grass.

Errands (without the world map): holding a story item (Oak's Parcel, the
S.S. Ticket...), head for the map that needs it (ERRANDS), through exits it
knows.

Outside the overworld (title screen, text, menus): A and B.
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field

from . import checklist, story
from .navigate import OBSTACLE_TRIES, Navigator
from .ram import GameState
from .world import LAND_ENCOUNTERS, WALL

DIRS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
FORGET_EVERY = 200  # at most this often, forget walls when the story flags change
HEAL_BELOW = 0.4  # go back to a known healing spot when the party's HP is below this
RUN_BELOW = 0.5  # run from wild battles when the party's HP is below this
HEAL_SEEN_WITHIN = 15  # a full heal this many presses after talking to someone: they heal
TRAIN_MARGIN = 2  # train until the strongest Pokémon is this close to the next Gym Leader's level
TRAIN_HP = 0.6  # only go training with at least this much HP
TRAINER_LEVEL_MARGIN = 3  # challenge trainers whose strongest is at most this many levels above ours
TRAINER_LOSSES = 2  # losses to one trainer before leaving them alone for a while
TRAIN_SHARE = 0.6  # share of overworld presses spent training (the rest keep exploring)
ERRAND_SHARE = 0.6  # share of overworld presses spent heading for an errand's destination
ERRAND_STEPS = 400  # presses to spend at an errand's destination before it counts as tried
NO_B_AFTER_LEVEL_UP = 80  # presses without B after a battle with a level-up (B cancels evolution)
STORY_SHARE = 0.95  # share of overworld presses spent on the checklist (the rest: a look around)
STORY_BUDGET = 3000  # presses on one story objective before putting it aside for a while
CHECK_BUDGET = 1500  # the same for a hack feature check
CHECK_GIVE_UP = 2  # a hack check put aside this many times is dropped as out of reach
STORY_REST = 1500  # presses an objective stays put aside

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
    def __init__(self, rng: random.Random | None = None, map_visits=None, interact_prob=0.02, menu_prob=0.003,
                 catch_prob=0.35, game=None, world=None):
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
        # Story: the world map and a navigator over it (when the game has one).
        self.nav = Navigator(world, game) if world is not None and game is not None else None
        self.objective: str | None = None  # the story objective being worked on
        self.story_presses: dict[str, int] = {}
        self.story_rest: dict[str, int] = {}  # objective -> press until which it's put aside
        self.story_target: dict[str, int] = {}  # objective -> which of its people to talk to next
        self.story_stalls: dict[str, int] = {}  # objective -> times it was put aside
        self._nurses = None
        self.train_maps: dict = {}  # (checklist item, its map) -> where to train for it
        self.trainer_target = None  # (trainer, press) when it last challenged one
        self.trainer_losses: dict[str, int] = {}
        self.trainer_rest: dict[str, int] = {}  # trainer -> press until which it's left alone
        # The checklist: hack checks this worker has settled (passed, failed, or out of reach),
        # the try being verified now, watches in progress, and what happened, for the tester.
        self.checked: set[str] = set()
        self.check_tries: dict[str, int] = {}
        self.wrong_switches: dict[str, int] = {}  # toggle check -> tries that switched another setting
        self.pending: dict | None = None
        self.watching: dict[str, int] = {}  # watch key -> press its `after` became true
        self.watch_prev: dict[str, bool] = {}
        self.story_prev: dict[str, bool] = {}
        self.field_tries: dict = {}  # obstacle tile -> (kind, tries)
        self.events: list[dict] = []  # {"key", "result": pass/fail/unreached, "detail"}

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
            if self.nav is not None:
                self.nav.plan_key = None  # find a way around it
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
        if s.valid and s.flags and self.nav is not None:
            self._follow_up(s)
        if self.queue:
            a = self.queue.popleft()
            if a.tag == "move" and s.valid:
                self.last_move = (s.map_id, s.x, s.y, a.buttons[0])
            return a
        if not s.valid:
            return tap(("A",) if self.rng.random() < 0.8 else ("START",), 30, "text")
        if s.in_battle:
            return self._battle(s)
        self._after_trainer(s)
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
        if self._wants_training(s) and self.rng.random() < TRAIN_SHARE:
            a = self._train(s)
            if a is not None:
                return a
        if self.nav is not None:
            if self.pending is not None:
                return Action((), 0, 30, "wait")  # let the last try show what it did
            if self.rng.random() < STORY_SHARE:
                a = self._story(s)
                if a is not None:
                    return a
        else:
            a = self._errand(s)
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
        if not live or not (self.heal_spots or self.nav is not None):
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

    # --- the story ------------------------------------------------------------------

    def _nav_to(self, s: GameState, key, goal) -> Action | None:
        """One press along the world map's way to a tile where goal(map, x, y) holds."""
        r = self.nav.step(s, key, goal, self.t, avoid=lambda: self.nav.avoid_from(self.maps))
        if r is None:
            return None
        kind, d = r
        if kind == "use":  # a Cut tree, a rock, a boulder, water: face it and press A (YES)
            dx, dy = DIRS[d]
            target = (self.nav.name(s.map_id), s.x + dx, s.y + dy)
            what = self.nav.obstacles(s)[1].get(target, "water")
            _k, tries = self.field_tries.get(target, (what, 0))
            self.field_tries[target] = (what, tries + 1)
            if (tries + 1 >= OBSTACLE_TRIES and what in checklist.FIELD_MOVES and what != "EventScript_StrengthBoulder"
                    and checklist.is_hack(self.game)):
                key, title = checklist.FIELD_MOVES[what]
                if key not in self.checked:
                    self._event(key, "fail", f"Pressed A at it {tries + 1} times at {target[0]} ({target[1]}, "
                                             f"{target[2]}) with the HM in the bag and the badge, and it stayed.")
            self._talk(s.map_id, s.x, s.y, d)
            return tap((d,), 10, "use")
        self.last_move = (s.map_id, s.x, s.y, d)
        return Action((d,), tag="move")

    def current_objective(self, s: GameState):
        if self.nav is None or not s.valid or not s.flags:
            return None
        return checklist.current(s, self.game, checked=self.checked)

    # --- the checklist: trying things and checking they worked ------------------------

    def _event(self, key: str, result: str, detail: str = "") -> None:
        self.checked.add(key)
        self.events.append({"key": key, "result": result, "detail": detail})

    def _follow_up(self, s: GameState) -> None:
        """Every press: see whether the last try worked, keep an eye on the watches,
        notice field moves working and story objectives getting done."""
        g = self.game
        p = self.pending
        if p is not None and p["verify"] == "toggle" and not s.in_battle:
            self._follow_up_toggle(s, p)
        elif p is not None and (not s.in_battle or p["verify"] in ("battle", "double")):
            c = checklist.BY_KEY[p["key"]]
            worked = {"done": lambda: c.done(s, g), "battle": lambda: s.in_battle,
                      "double": lambda: s.in_battle and bool(s.battle_type & 1),
                      "visit": lambda: not self.queue,
                      "toggle": lambda: not self.queue and self._flag(s, c.flag) != p["before"]}[c.verify]()
            if worked:
                self.pending = None
                if c.verify == "toggle" and not p.get("restoring"):
                    # It flipped: talk again to put it back as the run's rules had it.
                    self.check_tries[c.key] = 0
                    self._try_check(s, c, p["facing"], restoring=True)
                else:
                    self._event(c.key, "pass")
            elif self.t - p["t"] > checklist.VERIFY_WITHIN and not self.queue:
                self.pending = None
                tries = self.check_tries[c.key] = self.check_tries.get(c.key, 0) + 1
                if tries >= checklist.TRIES:
                    what = {"done": "it didn't happen", "battle": "no battle started",
                            "double": "no double battle started",
                            "toggle": f"{c.flag} didn't change", "visit": "it didn't finish"}[c.verify]
                    self._event(c.key, "fail", f"Tried {tries} times ({c.why}): {what}.")
        if self.t % 5:
            return
        hack = checklist.is_hack(g)
        for w in checklist.WATCHES if hack else ():
            now = w.after(s, g)
            if now and self.watch_prev.get(w.key) is False and w.key not in self.checked:
                self.watching[w.key] = self.t
            self.watch_prev[w.key] = now
            start = self.watching.get(w.key)
            if start is None:
                continue
            if w.expect(s, g):
                del self.watching[w.key]
                self._event(w.key, "pass")
            elif self.t - start > w.within:
                del self.watching[w.key]
                self._event(w.key, "fail", f"{w.within} presses after it, still nothing ({w.why}).")
        here = (self.nav.name(s.map_id), s.x, s.y)
        tried = self.field_tries.pop(here, None)
        if hack and tried is not None and tried[0] in checklist.FIELD_MOVES:
            key = checklist.FIELD_MOVES[tried[0]][0]
            if key not in self.checked:
                self._event(key, "pass")
        for o in story.STORY:
            now = o.done(s, g)
            if now and self.story_prev.get(o.key) is False:
                self.events.append({"key": o.key, "result": "pass", "detail": ""})
            self.story_prev[o.key] = now

    def _follow_up_toggle(self, s: GameState, p: dict) -> None:
        """A setting switch: after the presses that reach its YES/NO, press A one at a time
        until the flag flips (messages can run a page longer or shorter), then close the
        rest of the conversation with B (which can only answer NO from there on)."""
        c = checklist.BY_KEY[p["key"]]
        tidy = [tap(("B",), 40, "check") for _ in range(3)]
        others = [o for o in checklist.CHECKS if o.verify == "toggle" and o.flag != c.flag]
        wrong = next((o for o in others if self._flag(s, o.flag) != p["others"].get(o.flag)), None)
        if wrong is not None and not p.get("fixing"):
            # The wrong option got picked and switched another setting: put that one back
            # first (without counting it as that check's result), then try this one again.
            self.queue.clear()
            self.queue.extend(tidy)
            self.check_tries[c.key] = self.check_tries.get(c.key, 0) + 1
            self.wrong_switches[c.key] = self.wrong_switches.get(c.key, 0) + 1
            self._try_check(s, wrong, p["facing"], restoring=True)
            self.pending["fixing"] = True
            return
        if self._flag(s, c.flag) != p["before"]:
            self.queue.clear()  # that A answered YES: no more
            self.queue.extend(tidy)
            self.pending = None
            if p.get("fixing"):
                return  # put back; the check it interrupted gets tried again
            if p["restoring"]:
                self._event(c.key, "pass")
            else:
                # It flipped: talk again to put it back as the run's rules had it.
                self.check_tries[c.key] = 0
                self._try_check(s, c, p["facing"], restoring=True)
            return
        if self.queue:
            return
        if p["a_left"] > 0:
            p["a_left"] -= 1
            self.queue.append(tap(("A",), 40, "check"))
            return
        if self.t - p["t"] <= checklist.VERIFY_WITHIN:
            return
        self.pending = None
        self.queue.extend(tidy)
        tries = self.check_tries[c.key] = self.check_tries.get(c.key, 0) + 1
        if tries < checklist.TRIES:
            if p["restoring"]:  # keep trying to put it back, not to switch it again
                self._try_check(s, c, p["facing"], restoring=True)
            return
        if p.get("fixing"):
            self._event(c.key, "fail", f"Another check switched {c.flag} by mistake, and switching it back didn't "
                                       f"work. This run's rules are now different.")
        elif p["restoring"]:
            self._event(c.key, "fail", f"It switched {c.flag}, but switching it back didn't work after {tries} "
                                       f"tries ({c.why}). This run's rules are now different.")
        else:
            wrong = self.wrong_switches.get(c.key, 0)
            note = (f" {wrong} of the tries switched a different setting instead (put back each time): the "
                    "playtester probably picked the wrong option in the menu.") if wrong else ""
            self._event(c.key, "fail", f"Tried {tries} times ({c.why}): {c.flag} didn't change.{note}")

    def _flag(self, s, name) -> bool:
        n = self.game.flags.get(name)
        return n is not None and bool(s.flag(n))

    def _try_check(self, s, c, facing, restoring=False) -> Action:
        """Face them and do the check's presses; then wait and see whether it worked."""
        self.pending = {"key": c.key, "verify": c.verify, "t": self.t, "facing": facing, "restoring": restoring,
                        "before": self._flag(s, c.flag) if c.flag else None, "a_left": checklist.TOGGLE_A_PRESSES,
                        "others": {o.flag: self._flag(s, o.flag) for o in checklist.CHECKS if o.verify == "toggle"}}
        self.last_talk = (s.map_id, s.x, s.y, facing, self.t)
        if restoring:  # straight after the first conversation, from the queue
            self.queue.append(tap((facing,), 10, "check"))
        # The first A starts the conversation: give its message and menu time to appear.
        self.queue.extend(tap((b,), 120 if i == 0 else 40, "check") for i, b in enumerate(c.macro))
        return tap((facing,), 10, "check")

    def _story(self, s: GameState) -> Action | None:
        """One press towards the current checklist item, or None to look around."""
        if not self.nav.knows(s.map_id):
            return None
        resting = {k for k, until in self.story_rest.items() if until > self.t}
        o = checklist.current(s, self.game, skip=resting, checked=self.checked)
        self.objective = o.key if o else None
        if o is None:
            return None
        n = self.story_presses[o.key] = self.story_presses.get(o.key, 0) + 1
        if n % (STORY_BUDGET if o.part == "story" else CHECK_BUDGET) == 0:
            # Not getting anywhere: put it aside, look around, and come back to it later.
            self.story_rest[o.key] = self.t + STORY_REST
            self.story_stalls[o.key] = self.story_stalls.get(o.key, 0) + 1
            if o.part == "hack" and self.story_stalls[o.key] >= CHECK_GIVE_UP:
                self._event(o.key, "unreached", f"Couldn't get it done in {n} presses.")
            return None
        here = self.nav.name(s.map_id)
        steps = [st for st in o.steps if st.when(s, self.game)]
        if o.key.startswith("badge") and steps and steps[0].map.endswith("_Gym"):
            gym = steps[0].map  # the gym's trainers first, then the leader
            a = self._fight_trainers(s, lambda m: m == gym, gym)
            if a is not None:
                return a
        for st in steps:
            a = self._story_step(s, o, st, here)
            if a == "explore":
                return None
            if a is not None:
                return a
        if o.post_game and here not in {st.map for st in steps}:
            return self._ferry(s, o)
        return None

    def _story_step(self, s: GameState, o, st, here):
        """An Action for this step, "explore" (it's on the step's map with nothing better
        to do), or None (no way there: try the next step)."""
        nav = self.nav
        if st.talk:
            targets = nav.talk_spots(s, st.map, st.talk)
            for _ in range(len(targets)):
                i = self.story_target.get(o.key, 0) % len(targets)
                spots = {(st.map, x, y): d for x, y, d in targets[i]}
                facing = spots.get((here, s.x, s.y))
                if facing is not None:
                    self.story_target[o.key] = i + 1  # someone else next time
                    if getattr(o, "part", "story") == "hack":
                        return self._try_check(s, o, facing)
                    self._talk(s.map_id, s.x, s.y, facing)
                    return tap((facing,), 10, "story")
                a = self._nav_to(s, ("talk", o.key, i), lambda m, x, y, sp=spots: (m, x, y) in sp)
                if a is not None:
                    return a
                self.story_target[o.key] = i + 1  # no way to them: try the next
        if st.step:
            tiles = {(st.map, x, y) for x, y in nav.trigger_tiles(st.map, st.step)}
            if (here, s.x, s.y) in tiles:
                return "explore"  # on it: its script runs (or not); step about
            a = self._nav_to(s, ("step", o.key), lambda m, x, y: (m, x, y) in tiles)
            if a is not None:
                return a
        if here == st.map:
            return "explore"
        return self._nav_to(s, ("enter", st.map), lambda m, x, y: m == st.map)

    def _ferry(self, s: GameState, o) -> Action | None:
        """No way on foot to an island objective: find a Seagallop sailor and take the ferry
        (A to talk and say YES, a random island from the list, A)."""
        here = self.nav.name(s.map_id)
        m = self.nav.world.maps[here]
        for obj in m.objects:
            if any(p in obj[3] for p in story.FERRY_SAILORS):
                spots = {(here, x, y): d for x, y, d in self.nav.world.adjacent_spots(here, obj[1], obj[2])}
                facing = spots.get((here, s.x, s.y))
                if facing is not None:
                    self.queue.extend([tap(("A",), 40, "ferry") for _ in range(3)])
                    self.queue.extend([tap(("DOWN",), 20, "ferry") for _ in range(self.rng.randint(0, 3))])
                    self.queue.extend([tap(("A",), 60, "ferry") for _ in range(4)])
                    return tap((facing,), 10, "ferry")
                return self._nav_to(s, ("ferry", here), lambda mp, x, y: (mp, x, y) in spots)
        sailors = {}
        for name, mm in self.nav.world.maps.items():
            for obj in mm.objects:
                if any(p in obj[3] for p in story.FERRY_SAILORS):
                    sailors.update({(name, x, y): d for x, y, d in self.nav.world.adjacent_spots(name, obj[1], obj[2])})
        return self._nav_to(s, "ferry", lambda mp, x, y: (mp, x, y) in sailors)

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
        if self.game is None or not (self.grass or self.nav is not None):
            return False
        live = [mon for mon in s.party if not mon.is_egg]
        if not live or s.hp_fraction < TRAIN_HP:
            return False
        top = max(mon.level for mon in live)
        return top < self.game.next_gym_level(s) - TRAIN_MARGIN

    def _training_map(self, s: GameState) -> str | None:
        """Where to train: the last map with grass (or a cave) on the way to the current checklist
        item. Wild Pokémon get stronger along the story, so that's where Exp. comes fastest."""
        o = self.current_objective(s)
        st = story.next_step(o, s, self.game) if o is not None else None
        if st is None:
            return None
        key = (o.key, st.map)
        if key not in self.train_maps:
            nav, world = self.nav, self.nav.world
            here = (nav.name(s.map_id), s.x, s.y)
            plan = world.route(here, lambda m, x, y: m == st.map, surf=story.CAN_SURF(s, self.game),
                               blocked=nav.obstacles(s)[0]) or []
            maps = list(dict.fromkeys([p[0] for p in plan] + [st.map]))
            with_grass = [m for m in maps if world.maps[m].grass()]
            self.train_maps[key] = with_grass[-1] if with_grass else None
        return self.train_maps[key]

    def _train_world(self, s: GameState) -> Action | None:
        """Walk to grass (or cave floor) on the training map, or the nearest if there's none,
        then pace about in it."""
        world = self.nav.world
        here = self.nav.name(s.map_id)
        m = world.maps[here]
        where = self._training_map(s)

        def grass(x, y, mm=m):
            c = mm.cell(x, y)
            return c is not None and bool(c & LAND_ENCOUNTERS) and not c & WALL

        if grass(s.x, s.y) and where in (None, here):
            mem = self.mem(s.map_id)
            options = [d for d, (dx, dy) in DIRS.items()
                       if grass(s.x + dx, s.y + dy) and (s.x, s.y, d) not in mem.blocked]
            if not options:
                return None
            d = self.rng.choice(options)
            self.last_move = (s.map_id, s.x, s.y, d)
            return Action((d,), tag="move")
        if where is not None:
            a = self._nav_to(s, ("train", where), lambda mp, x, y: mp == where and grass(x, y, world.maps[mp]))
            if a is not None:
                return a
        return self._nav_to(s, "train", lambda mp, x, y: grass(x, y, world.maps[mp]))

    # --- trainer battles -----------------------------------------------------------

    def _next_gym(self, s: GameState) -> str | None:
        for o in story.STORY:
            if o.key.startswith("badge") and not o.done(s, self.game):
                return o.steps[0].map
        return None

    def _fight_trainers(self, s: GameState, maps, key) -> Action | None:
        """Walk to the nearest trainer still to beat on `maps` and challenge them."""
        top = max((m.level for m in s.party if not m.is_egg), default=0)
        resting = {t for t, until in self.trainer_rest.items() if until > self.t}
        spots = self.nav.trainer_spots(s, maps, top + TRAINER_LEVEL_MARGIN, resting)
        if not spots:
            return None
        here = (self.nav.name(s.map_id), s.x, s.y)
        if here in spots:
            tid, facing = spots[here]
            self.trainer_target = (tid, self.t)
            self._talk(s.map_id, s.x, s.y, facing)
            return tap((facing,), 10, "trainer")
        return self._nav_to(s, ("trainers", key, len(spots)), lambda m, x, y: (m, x, y) in spots)

    def _after_trainer(self, s: GameState) -> None:
        """After challenging a trainer: count a loss, or leave alone one that wouldn't battle."""
        target = self.trainer_target
        if target is None or s.in_battle or not s.valid:
            return
        tid, t = target
        n = self.game.trainer_ids.get(tid)
        if n is not None and s.flag(self.game.trainer_flags_start + n):
            self.trainer_target = None  # beaten
        elif self.was_in_battle:
            self.trainer_target = None  # lost
            self.trainer_losses[tid] = self.trainer_losses.get(tid, 0) + 1
            if self.trainer_losses[tid] >= TRAINER_LOSSES:
                self.trainer_losses[tid] = 0
                self.trainer_rest[tid] = self.t + STORY_REST
        elif self.t - t > 40:
            self.trainer_target = None  # no battle: someone moved, or it's not their turn yet
            self.trainer_rest[tid] = self.t + STORY_REST

    def _train(self, s: GameState) -> Action | None:
        """Trainers first (outside gyms, then the next gym's), then wild Pokémon in grass."""
        if self.nav is not None and self.nav.knows(s.map_id):
            a = self._fight_trainers(s, lambda m: not m.endswith("_Gym"), "outside")
            gym = self._next_gym(s)
            if a is None and gym is not None:
                a = self._fight_trainers(s, lambda m: m == gym, gym)
            if a is None:
                a = self._train_world(s)
            if a is not None:
                return a
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

    def _heal_here(self, s: GameState, x, y, facing) -> Action | None:
        """At a healing spot: face them and talk, or give up on the spot after a few tries."""
        if self.heal_attempt is not None and self.t - self.heal_attempt < 40:
            return None  # just tried: let the result show before trying again
        if self.heal_attempt is not None:
            # Talked here before and still hurt: after a few tries, forget the spot.
            self.heal_fails[s.map_id] = self.heal_fails.get(s.map_id, 0) + 1
            if self.heal_fails[s.map_id] >= 3:
                self.heal_spots.pop(s.map_id, None)
                self.heal_attempt = None
                return None
        self.heal_attempt = self.t
        self._talk(s.map_id, x, y, facing)
        return tap((facing,), 10, "heal")  # face them first

    def _go_heal_world(self, s: GameState) -> Action | None:
        """The nearest Pokémon Center nurse (or other spot that healed before), by the world map."""
        nav = self.nav
        if self._nurses is None:
            self._nurses = nav.nurse_spots()
        spots = {k: d for k, d in self._nurses.items()
                 if self.heal_fails.get(nav.id_by_name.get(k[0]), 0) < 3}
        for map_id, (x, y, facing) in self.heal_spots.items():
            spots[(nav.name(map_id), x, y)] = facing
        here = (nav.name(s.map_id), s.x, s.y)
        if here in spots:
            return self._heal_here(s, s.x, s.y, spots[here])
        return self._nav_to(s, "heal", lambda m, x, y: (m, x, y) in spots)

    def _go_heal(self, s: GameState) -> Action | None:
        """One step towards the nearest known healing spot, or talk to it once there."""
        if self.nav is not None and self.nav.knows(s.map_id):
            a = self._go_heal_world(s)
            if a is not None or self.heal_attempt is not None and self.t - self.heal_attempt < 40:
                return a
        if not self.heal_spots:
            return None
        route = self._map_route(s.map_id, set(self.heal_spots))
        if route is None:
            return None
        m = self.mem(s.map_id)
        here = (s.x, s.y)
        if len(route) == 1:
            x, y, facing = self.heal_spots[s.map_id]
            if here == (x, y):
                return self._heal_here(s, x, y, facing)
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
