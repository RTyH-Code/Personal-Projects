"""Reward shaping.

FireRed's real goal (beat the Elite Four) is thousands of steps away, so a
fresh agent would never see it. Instead it gets small rewards for things
that tend to lead there: seeing new places, leveling up, catching Pokémon
and earning badges.

Most terms are "progress scores" that only ever go up, and the reward for a
step is how much the total went up. That way the agent can't farm reward by
undoing and redoing something (like depositing and withdrawing a Pokémon).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .ram import GameState

DEFAULT_WEIGHTS = {
    "explore": 0.02,  # per new tile stood on
    "new_map": 0.5,  # per new map entered
    "level": 1.0,  # per level gained (highest party level total so far)
    "badge": 20.0,  # per badge
    "dex": 2.0,  # per newly caught species
    "starter": 5.0,  # once, for getting the first Pokémon
    "pokedex": 5.0,  # once, for getting the Pokédex
    "heal": 1.0,  # per full party heal (Pokémon Center, potions)
    "blackout": -2.0,  # each time the whole party faints
}


@dataclass
class RewardTracker:
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    def __post_init__(self) -> None:
        self.weights = {**DEFAULT_WEIGHTS, **self.weights}
        self.reset(None)

    def reset(self, state: GameState | None) -> None:
        self.tiles: dict[tuple[int, int], set[tuple[int, int]]] = {}  # map -> (x, y)
        self.tile_count = 0
        self.totals = {k: 0.0 for k in self.weights}
        self.max_level_sum = 0
        self.max_badges = 0
        self.max_dex = 0
        self.prev: GameState | None = None
        if state is not None and state.valid:
            # Whatever the start state already has is not something to reward.
            self._visit(state)
            self.max_level_sum = state.level_sum
            self.max_badges = state.badge_count
            self.max_dex = state.dex_owned
            self.prev = state

    def _visit(self, s: GameState) -> tuple[bool, bool]:
        new_map = s.map_id not in self.tiles
        seen = self.tiles.setdefault(s.map_id, set())
        new_tile = (s.x, s.y) not in seen
        if new_tile:
            seen.add((s.x, s.y))
            self.tile_count += 1
        return new_map, new_tile

    def step(self, s: GameState) -> float:
        if not s.valid:
            return 0.0
        w = self.weights
        got: dict[str, float] = {}

        if not s.in_battle:
            new_map, new_tile = self._visit(s)
            if new_tile:
                got["explore"] = w["explore"]
            if new_map:
                got["new_map"] = w["new_map"]

        if s.level_sum > self.max_level_sum:
            # The first Pokémon's levels come with the "starter" reward.
            if self.max_level_sum > 0:
                got["level"] = w["level"] * (s.level_sum - self.max_level_sum)
            self.max_level_sum = s.level_sum
        if s.badge_count > self.max_badges:
            got["badge"] = w["badge"] * (s.badge_count - self.max_badges)
            self.max_badges = s.badge_count
        if s.dex_owned > self.max_dex:
            got["dex"] = w["dex"] * (s.dex_owned - self.max_dex)
            self.max_dex = s.dex_owned

        p = self.prev
        if p is not None and p.valid:
            if s.has_pokemon and not p.has_pokemon:
                got["starter"] = w["starter"]
            if s.has_pokedex and not p.has_pokedex:
                got["pokedex"] = w["pokedex"]
            same_party = len(s.party) == len(p.party) and s.level_sum == p.level_sum
            if same_party and s.hp_fraction > p.hp_fraction and not s.in_battle and not p.all_fainted:
                got["heal"] = w["heal"] * (s.hp_fraction - p.hp_fraction)
            if s.all_fainted and not p.all_fainted:
                got["blackout"] = w["blackout"]

        self.prev = s
        for k, v in got.items():
            self.totals[k] += v
        return sum(got.values())
