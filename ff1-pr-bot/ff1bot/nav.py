"""Getting around maps without a map of the walls.

The bot doesn't know where walls are up front. It plans the shortest route assuming
unknown ground is walkable, takes a step, and if the position didn't change it
remembers that step as blocked and plans again, like the FireRed explorer does.
What it learns is saved per map, so each map only has to be bumped into once.
"""

from __future__ import annotations

import heapq
import json
from pathlib import Path
from typing import Protocol

STEPS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


class World(Protocol):
    def position(self) -> tuple[int, int, int]:
        """(map_id, x, y), with y growing downwards on screen."""

    def in_battle(self) -> bool: ...

    def step(self, direction: str) -> None:
        """Try to walk one tile."""


class Navigator:
    def __init__(self, save_path: Path | None = None, margin: int = 30):
        self.save_path = save_path
        self.margin = margin
        self.blocked: dict[int, set[tuple[int, int, str]]] = {}
        if save_path and save_path.exists():
            data = json.loads(save_path.read_text(encoding="utf-8"))
            self.blocked = {int(m): {(x, y, d) for x, y, d in edges} for m, edges in data.items()}

    def save(self) -> None:
        if self.save_path:
            data = {str(m): sorted(edges) for m, edges in self.blocked.items()}
            self.save_path.write_text(json.dumps(data), encoding="utf-8")

    def record(self, map_id: int, frm: tuple[int, int], direction: str, to: tuple[int, int]) -> None:
        if to == frm:
            self.blocked.setdefault(map_id, set()).add((frm[0], frm[1], direction))

    def plan(self, map_id: int, start: tuple[int, int], goal: tuple[int, int]) -> list[str] | None:
        """Shortest list of directions from start to goal, avoiding known-blocked steps."""
        if start == goal:
            return []
        blocked = self.blocked.get(map_id, set())
        lo_x, hi_x = min(start[0], goal[0]) - self.margin, max(start[0], goal[0]) + self.margin
        lo_y, hi_y = min(start[1], goal[1]) - self.margin, max(start[1], goal[1]) + self.margin
        h = lambda p: abs(p[0] - goal[0]) + abs(p[1] - goal[1])  # noqa: E731
        frontier = [(h(start), 0, start)]
        came: dict[tuple[int, int], tuple[tuple[int, int], str] | None] = {start: None}
        cost = {start: 0}
        while frontier:
            _, g, cur = heapq.heappop(frontier)
            if cur == goal:
                path = []
                while came[cur] is not None:
                    cur, d = came[cur]
                    path.append(d)
                return path[::-1]
            if g > cost[cur]:
                continue
            for d, (dx, dy) in STEPS.items():
                if (cur[0], cur[1], d) in blocked:
                    continue
                nxt = (cur[0] + dx, cur[1] + dy)
                if not (lo_x <= nxt[0] <= hi_x and lo_y <= nxt[1] <= hi_y):
                    continue
                if g + 1 < cost.get(nxt, 1 << 30):
                    cost[nxt] = g + 1
                    came[nxt] = (cur, d)
                    heapq.heappush(frontier, (g + 1 + h(nxt), g + 1, nxt))
        return None


def walk_to(world: World, nav: Navigator, goal: tuple[int, int], max_steps: int = 500) -> str:
    """Walks to goal on the current map. Returns 'arrived', 'battle', 'map_changed', 'unreachable' or 'gave_up'."""
    map_id, x, y = world.position()
    for _ in range(max_steps):
        if (x, y) == goal:
            nav.save()
            return "arrived"
        route = nav.plan(map_id, (x, y), goal)
        if route is None:
            nav.save()
            return "unreachable"
        direction = route[0]
        world.step(direction)
        if world.in_battle():
            nav.save()
            return "battle"
        new_map, nx, ny = world.position()
        if new_map != map_id:
            nav.save()
            return "map_changed"
        nav.record(map_id, (x, y), direction, (nx, ny))
        x, y = nx, ny
    nav.save()
    return "gave_up"
