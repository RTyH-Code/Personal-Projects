"""Let later episodes start where earlier ones got to.

A full playthrough is hundreds of thousands of button presses, far longer
than one episode. So whenever an agent reaches a new milestone (a new map,
level, species, badge or the Hall of Fame), its save state goes into a pool
on disk. Each new episode usually starts from one of the best states in the
pool, so progress builds up across episodes. All the parallel emulators
share the same pool.

Each state also keeps the tiles explored on the way there, so the agent
isn't paid again for walking over old ground.
"""

from __future__ import annotations

import gzip
import json
import os
import random
import uuid
from pathlib import Path

from .goals import Goals
from .ram import GameState


def progress_score(s: GameState, goals: Goals, maps_explored: int, tiles_explored: int) -> int:
    """How far into the game a state is. Higher is further."""
    dex = goals.pokedex.progress(s.owned)[0] if goals.pokedex is not None else s.dex_owned
    return (
        100_000 * s.champion
        + 10_000 * s.badge_count
        + 200 * dex
        + 100 * maps_explored
        + 10 * s.level_sum
        + tiles_explored
    )


# Save a new state once the score is this much past the last one saved
# (e.g. 50 new tiles, 5 levels, or any new map, species or badge).
MIN_GAIN = 50


class ProgressPool:
    def __init__(self, directory: str | os.PathLike, keep: int = 64, sample_top: int = 8):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.keep = keep
        self.sample_top = sample_top

    def _entries(self) -> list[tuple[float, Path]]:
        out = []
        for p in self.dir.glob("*.state"):
            try:
                out.append((float(p.name.split("_", 1)[0]), p))
            except ValueError:
                continue
        return sorted(out, reverse=True)

    def best_score(self) -> float:
        e = self._entries()
        return e[0][0] if e else float("-inf")

    def worth_saving(self, score: float) -> bool:
        e = self._entries()
        return len(e) < self.keep or score > e[-1][0]

    def add(self, score: float, state: bytes, tiles, info: dict) -> Path:
        name = f"{score:012.1f}_{info.get('map', 'map')}_{uuid.uuid4().hex[:8]}"
        meta = self.dir / f"{name}.json.gz"
        meta.write_bytes(gzip.compress(json.dumps({"score": score, "info": info, "tiles": tiles}).encode()))
        path = self.dir / f"{name}.state"
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(gzip.compress(state))
        tmp.replace(path)  # appears atomically, so other processes never see half a file
        for _, old in self._entries()[self.keep :]:
            for f in (old, old.with_name(old.name[: -len(".state")] + ".json.gz")):
                f.unlink(missing_ok=True)
        return path

    def sample(self, rng: random.Random):
        """(state, tiles, score) from one of the best states, or None if empty."""
        for _ in range(3):  # another process may delete a file under us
            top = self._entries()[: self.sample_top]
            if not top:
                return None
            score, path = rng.choice(top)
            try:
                state = gzip.decompress(path.read_bytes())
                meta = json.loads(gzip.decompress(path.with_name(path.name[: -len(".state")] + ".json.gz").read_bytes()))
                return state, [tuple(t) for t in meta["tiles"]], score
            except (FileNotFoundError, OSError, ValueError):
                continue
        return None
