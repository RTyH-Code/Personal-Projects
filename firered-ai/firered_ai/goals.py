"""The end state the agent works towards: badges, champion and a complete Pokédex.

How it gets there, and in what order, is up to the agent. The goals only
decide what counts as progress, when a run is finished, and the bonus for
finishing.

What "complete Pokédex" means depends on the game. The lists in
firered_ai/data/ were generated from the game's source by
tools/pokedex_targets.py: every species one save can own without trading or
Mystery Gift. Some are either/or (the starter, which also decides the roaming
legendary, and in vanilla the Mt. Moon fossil); one option of each is enough.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .ram import GameState

DATA = Path(__file__).parent / "data"
GOAL_NAMES = ("badges", "champion", "pokedex")

def detect_game(rom_path: str) -> str | None:
    """The Pokédex list for a ROM: its game profile's name, or None if it isn't FireRed."""
    from .game import detect

    try:
        return detect(rom_path)[0].name
    except ValueError:
        return None


@dataclass
class PokedexTarget:
    game: str
    required: frozenset[int]
    choices: list[list[frozenset[int]]] = field(default_factory=list)
    names: dict[int, str] = field(default_factory=dict)

    @classmethod
    def load(cls, name_or_path: str) -> "PokedexTarget":
        path = Path(name_or_path)
        if not path.exists():
            path = DATA / f"pokedex_{name_or_path.replace('-', '_')}.json"
        d = json.loads(path.read_text())
        return cls(
            game=d.get("game", path.stem),
            required=frozenset(d["required"]),
            choices=[[frozenset(a) for a in alts] for alts in d.get("choices", [])],
            names={int(k): v for k, v in d.get("names", {}).items()},
        )

    @property
    def species(self) -> frozenset[int]:
        """Every species that counts towards the goal."""
        out = set(self.required)
        for alts in self.choices:
            for a in alts:
                out |= a
        return frozenset(out)

    def _best(self, alts, owned):
        # The option with the most already caught; ties go to the one with least left.
        return max(alts, key=lambda a: (len(a & owned), -len(a - owned)))

    def progress(self, owned: frozenset[int]) -> tuple[int, int]:
        """(have, need) for a complete Pokédex."""
        have, need = len(self.required & owned), len(self.required)
        for alts in self.choices:
            best = self._best(alts, owned)
            have += len(best & owned)
            need += len(best)
        return have, need

    def missing(self, owned: frozenset[int]) -> list[int]:
        out = set(self.required - owned)
        for alts in self.choices:
            out |= self._best(alts, owned) - owned
        return sorted(out)

    def complete(self, owned: frozenset[int]) -> bool:
        have, need = self.progress(owned)
        return have == need


@dataclass
class Goals:
    badges: bool = True
    champion: bool = True
    pokedex: PokedexTarget | None = None

    @classmethod
    def parse(cls, spec: str, pokedex: PokedexTarget | None) -> "Goals":
        """`spec` is a comma-separated list like "badges,champion,pokedex", or "none"."""
        names = {s.strip() for s in spec.split(",") if s.strip() and s.strip() != "none"}
        unknown = names - set(GOAL_NAMES)
        if unknown:
            raise ValueError(f"unknown goal(s): {', '.join(sorted(unknown))}; choose from {', '.join(GOAL_NAMES)}")
        if "pokedex" in names and pokedex is None:
            raise ValueError("the pokedex goal needs a Pokédex list (--pokedex)")
        return cls("badges" in names, "champion" in names, pokedex if "pokedex" in names else None)

    @property
    def any(self) -> bool:
        return self.badges or self.champion or self.pokedex is not None

    def status(self, s: GameState) -> dict[str, float]:
        out = {}
        if self.badges:
            out["badges"] = s.badge_count / 8
        if self.champion:
            out["champion"] = float(s.champion)
        if self.pokedex is not None:
            have, need = self.pokedex.progress(s.owned)
            out["pokedex"] = have / need if need else 1.0
        return out

    def fraction(self, s: GameState) -> float:
        """0..1, each goal weighted equally."""
        st = self.status(s)
        return sum(st.values()) / len(st) if st else 0.0

    def complete(self, s: GameState) -> bool:
        return self.any and s.valid and all(v >= 1.0 for v in self.status(s).values())

    def describe(self) -> str:
        parts = []
        if self.badges:
            parts.append("all 8 badges")
        if self.champion:
            parts.append("become Champion")
        if self.pokedex is not None:
            _, need = self.pokedex.progress(frozenset())
            parts.append(f"a complete Pokédex ({need} species, {self.pokedex.game})")
        return ", ".join(parts) or "none (open-ended)"
