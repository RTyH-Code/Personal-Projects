"""Bug detectors: what the playtester watches for while it plays.

Each step the tester hands the detectors the game state, the buttons it just
pressed and a hash of the screen. They return Findings. Values that could be
caught mid-update (the game writes some data over several frames) must stay
wrong for two steps in a row before they count.

Kinds of finding, by severity:
- crash:   the game stopped running (it no longer reads the buttons).
- softlock: the game runs but nothing changes, or the player can't move.
- corrupt: impossible data: a Bad Egg, a broken party, overflowed money or
           Exp., an unknown map, a bad bag slot.
- rule:    a challenge rule or the level cap didn't hold.
- setup:   the playtester's own data looks wrong for this ROM (it says so
           once and stops the checks that depend on it).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .game import Game
from .ram import GameState

KEY_BITS = {"A": 0, "B": 1, "SELECT": 2, "START": 3, "RIGHT": 4, "LEFT": 5, "UP": 6, "DOWN": 7, "R": 8, "L": 9}
MAX_EXP = 1_640_000  # the most any growth rate needs for level 100

# How long things must last before they count, in tester steps (one step is
# a button press plus a wait, about 0.4 s of game time).
HANG_STEPS = 30
FROZEN_STEPS = 900
STUCK_STEPS = 4000


@dataclass
class Finding:
    kind: str  # crash, softlock, corrupt, rule
    check: str  # which detector
    title: str
    detail: str
    map: str = ""
    step: int = 0
    fatal: bool = False  # the session can't continue
    reproducible: bool = True  # can be re-run from a save state shortly before
    extra: dict = field(default_factory=dict)

    @property
    def signature(self) -> str:
        return f"{self.check}|{self.title}|{self.map}"


def key_mask(buttons) -> int:
    return sum(1 << KEY_BITS[b] for b in buttons)


class Detectors:
    def __init__(self, game: Game):
        self.game = game
        self.reset()

    def reset(self) -> None:
        self.prev: GameState | None = None
        self.presses: list[tuple[int, int]] = []  # (buttons pressed, gMain.heldKeysRaw) for recent presses
        self.same_screen = 0
        self.last_screen = None
        self.still = 0
        self.last_place = None
        self.pending: dict[str, int] = {}  # signature -> consecutive steps seen
        self.mons: dict[int, tuple[int, int]] = {}  # personality -> highest (level, exp) seen
        self.drops: dict[int, int] = {}  # personality -> steps its level or Exp. has been below that
        self.battle: dict | None = None
        self.areas_confirmed = False
        self.first_valid = True
        self.trust_key = True  # money and bag quantities are decrypted with the save's key

    # --- helpers ------------------------------------------------------------

    def _persist(self, key: str, bad: bool, seen: set) -> bool:
        """True the second step running that `key` is bad."""
        if not bad:
            return False
        seen.add(key)
        self.pending[key] = self.pending.get(key, 0) + 1
        return self.pending[key] == 2

    def _rules(self, s: GameState) -> dict[str, bool]:
        f = self.game.flags
        def on(name):
            return name in f and s.flag(f[name])
        return {
            "nuzlocke": on("HACK_NUZLOCKE") and s.has_pokedex,
            "no_items": on("HACK_NO_BATTLE_ITEMS"),
            "level_caps": on("HACK_LEVEL_CAP"),
        }

    # --- the checks ---------------------------------------------------------

    def check(self, s: GameState, buttons=(), screen_hash=None, held_during_press=None, step=0,
              last_was_move=False) -> list[Finding]:
        g = self.game
        out: list[Finding] = []
        seen: set[str] = set()
        place = g.map_name(*s.map_id) if s.valid else "(no save loaded)"

        def add(kind, check, title, detail, **kw):
            out.append(Finding(kind, check, title, detail, map=place, step=step, **kw))

        # The game's main loop copies the pressed buttons into gMain.heldKeysRaw
        # every frame. If it stops doing that, the game has crashed or hung.
        # A crash can leave a stale value behind (say A, if A was down), so the
        # sign is that the value stops changing while different buttons are pressed.
        held = s.held_keys if held_during_press is None else held_during_press
        if buttons:
            self.presses = (self.presses + [(key_mask(buttons), held)])[-HANG_STEPS:]
            if (len(self.presses) == HANG_STEPS and len({h for _, h in self.presses}) == 1
                    and len({m for m, _ in self.presses}) >= 3
                    and any(m & h != m for m, h in self.presses)):
                self.presses = []
                add("crash", "hang", "The game stopped responding to buttons",
                    f"For {HANG_STEPS} presses of different buttons the game's record of held buttons "
                    f"(gMain.heldKeysRaw) didn't change from {held:#x}. It has crashed or is stuck in a loop.",
                    fatal=True)

        if screen_hash is not None:
            self.same_screen = self.same_screen + 1 if screen_hash == self.last_screen else 0
            self.last_screen = screen_hash
            if self.same_screen == FROZEN_STEPS:
                add("softlock", "frozen", "The screen stopped changing",
                    f"The picture stayed exactly the same for {FROZEN_STEPS} presses (about "
                    f"{FROZEN_STEPS * 24 // 3600} minutes) of A, B, START and directions.", fatal=True,
                    reproducible=False)

        if not s.valid:
            self.prev = s
            return out

        here = (s.map_id, s.x, s.y)
        self.still = self.still + 1 if here == self.last_place and not s.in_battle else 0
        self.last_place = here
        if self.still == STUCK_STEPS:
            add("softlock", "stuck", "The player couldn't move for a long time",
                f"Same map and position, not in battle, for {STUCK_STEPS} presses (about "
                f"{STUCK_STEPS * 24 // 3600} minutes) despite trying every direction, A and B. "
                "Possibly trapped, or a script never released the player.", fatal=True, reproducible=False)

        if self.first_valid:
            # Money and bag quantities are both encrypted with the key whose
            # offset moves with the species count. If both look impossible
            # straight away, the profile's save layout is wrong for this ROM.
            self.first_valid = False
            bad_bag = any(q == 0 or q > 999 for items in s.bag.values() for _, q in items)
            if s.raw_money > 999_999 and bad_bag:
                self.trust_key = False
                add("setup", "layout", "The save layout doesn't match this ROM",
                    "Money and bag quantities don't decrypt to sensible values, so the encryption key offset is "
                    "probably wrong for this release. Money and bag checks are off; regenerate the game profile "
                    "(tools/game_data.py).", reproducible=False)

        if s.map_id not in g.maps and self._persist("map", True, seen):
            add("corrupt", "map", "Unknown map", f"The game is on map group {s.map_group}, number {s.map_num}, "
                "which doesn't exist.")

        if self._persist("party_count", s.party_count > 6, seen):
            add("corrupt", "party", "Party count is over 6", f"gPlayerPartyCount is {s.party_count}.")

        for i, m in enumerate(s.party):
            name = g.species_name(m.species)
            problems = []
            if not m.checksum_ok or m.bad_egg:
                problems.append(("Bad Egg / corrupt Pokémon data",
                                 "its encrypted data doesn't match its checksum" if not m.checksum_ok else
                                 "the game flagged it as a Bad Egg"))
            elif m.species not in g.species:
                problems.append(("Invalid species", f"species number {m.species} doesn't exist"))
            elif not m.is_egg:
                if not 1 <= m.level <= 100:
                    problems.append(("Level out of range", f"level {m.level}"))
                if m.max_hp == 0:
                    problems.append(("Zero max HP", "max HP is 0"))
                if m.raw_hp > m.max_hp:
                    problems.append(("HP above max", f"HP {m.raw_hp} / {m.max_hp}"))
                if m.exp > MAX_EXP:
                    problems.append(("Exp. overflow", f"Exp. is {m.exp} (more than any Pokémon can have)"))
                if any(v == 0 for v in m.stats):
                    problems.append(("Zero stat", f"stats {m.stats}"))
            for title, why in problems:
                if self._persist(f"mon{i}|{title}", True, seen):
                    add("corrupt", "party", title, f"Party slot {i + 1} ({name}, Lv. {m.level}): {why}.",
                        extra={"slot": i, "species": name})

        if self._persist("money", self.trust_key and s.raw_money > 999_999, seen):
            add("corrupt", "money", "Money over the limit", f"Money is {s.raw_money} (the cap is 999,999).")

        for pocket, items in (s.bag.items() if self.trust_key else ()):
            for item, qty in items:
                if item > g.items_count or qty == 0 or qty > 999:
                    if self._persist(f"bag|{pocket}|{item}", True, seen):
                        add("corrupt", "bag", "Bad bag slot", f"{pocket.replace('_', ' ')} pocket: item {item}, "
                            f"quantity {qty}.")

        self._mon_progress(s, seen, add)
        self._battles(s, add, last_was_move)

        rules = self._rules(s)
        if rules["nuzlocke"]:
            for i, m in enumerate(s.party):
                if self._persist(f"dead{i}", m.nuzlocke_dead and m.hp > 0 and not m.is_egg, seen):
                    add("rule", "nuzlocke", "A fainted Nuzlocke Pokémon has HP again",
                        f"Party slot {i + 1} ({g.species_name(m.species)}) is marked as fainted for good but has "
                        f"{m.hp} HP.")

        for k in list(self.pending):
            if k not in seen:
                del self.pending[k]
        self.prev = s
        return out

    def _mon_progress(self, s: GameState, seen, add) -> None:
        """Levels and Exp. never go down, and Exp. can't carry a Pokémon past the level cap."""
        cap = self.game.level_cap(s)
        current = {}
        for i, m in enumerate(s.party):
            if m.is_egg or not m.checksum_ok:
                continue
            before = self.mons.get(m.personality)
            if before is None:
                current[m.personality] = (m.level, m.exp)
                continue
            level, exp = before
            name = self.game.species_name(m.species)
            if m.level < level or m.exp < exp:
                # Count it once it lasts two steps (not a read mid-update), then
                # accept the new values so it's reported once.
                self.drops[m.personality] = self.drops.get(m.personality, 0) + 1
                if self.drops[m.personality] == 2:
                    add("corrupt", "progress", "Level or Exp. went down",
                        f"{name} went from Lv. {level} ({exp} Exp.) to Lv. {m.level} ({m.exp} Exp.).")
                    current[m.personality] = (m.level, m.exp)
                continue
            self.drops.pop(m.personality, None)
            if m.level > level and m.level > cap:
                add("rule", "level_cap", "Leveled past the level cap",
                    f"{name} went from Lv. {level} to Lv. {m.level}; the cap is Lv. {cap}.")
            current[m.personality] = (m.level, m.exp)
        # Remember Pokémon that left the party too (deposited ones come back later).
        self.mons.update(current)

    def _battles(self, s: GameState, add, last_was_move) -> None:
        """Rules that can only be judged over a whole battle."""
        p = self.prev
        if p is None or not p.valid:
            return
        g = self.game
        bt = g.p.get("battle_types", {})
        if s.in_battle and not p.in_battle:
            exempt = sum(bt.get(k, 0) for k in ("TRAINER", "LINK", "POKEDUDE", "OLD_MAN_TUTORIAL", "GHOST"))
            sec = g.maps.get(s.map_id, {}).get("section_index")
            area = None if sec is None else sec - g.p.get("kanto_mapsec_start", 0)
            self.battle = {
                "rules": self._rules(s),
                "bag": {it: q for pocket in ("items", "berries") for it, q in s.bag.get(pocket, [])},
                "party": len(s.party),
                "owned": s.owned,
                "area": area,
                "area_used": self._area_used(s, area),
                "random_wild": not (s.battle_type & exempt) and last_was_move,
                "shiny": bool(s.enemy and s.enemy.is_shiny(g.p.get("shiny_odds", 8))),
                "enemy": g.species_name(s.enemy.species) if s.enemy else "?",
            }
            return
        if not (p.in_battle and not s.in_battle and self.battle):
            return
        b, self.battle = self.battle, None
        if b["rules"]["no_items"]:
            for item, q in b["bag"].items():
                after = s.item_count(item)
                if after < q:
                    add("rule", "no_items", "A bag item was used in battle with NO ITEMS IN BATTLE on",
                        f"Item {item} went from {q} to {after} during a battle.")
        caught = len(s.party) > b["party"] or bool(s.owned - b["owned"])
        area = b["area"]
        if area is not None and self._area_used(s, area) and not b["area_used"] and b["random_wild"]:
            self.areas_confirmed = True  # the game set the bit we expected: the offset is right
        if (b["rules"]["nuzlocke"] and caught and b["random_wild"] and b["area_used"] and not b["shiny"]
                and self.areas_confirmed):
            add("rule", "nuzlocke", "Caught a second Pokémon in a used Nuzlocke area",
                f"Caught {b['enemy']} in an area whose Nuzlocke encounter was already used.")

    def _area_used(self, s: GameState, area) -> bool:
        if area is None or not s.nuzlocke_areas or not 0 <= area < 8 * len(s.nuzlocke_areas):
            return False
        return bool(s.nuzlocke_areas[area // 8] >> (area % 8) & 1)
