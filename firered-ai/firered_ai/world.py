"""The whole world map, and finding a way across it.

Loaded from firered_ai/data/games/<game>.world.json.gz (made by
tools/world_data.py from the game's source): every map's tiles (wall, water,
grass, ledge), its warps (doors, stairs) and connections (walking off one
route's edge onto the next), plus its people, signs and trigger tiles.

route() finds the shortest walk from one tile to any tile matching a goal,
across maps: walking, warps, connections, ledges (one way only), and water
only when Surf is allowed. People and Cut trees aren't in the tile grid, so
the explorer's own memory of what blocked it is passed in as `avoid`.
"""

from __future__ import annotations

import base64
import gzip
import json
from collections import deque
from functools import cached_property
from pathlib import Path

GAMES = Path(__file__).parent / "data" / "games"
DIRS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
CONNECTION_DIRS = {"up": "UP", "down": "DOWN", "left": "LEFT", "right": "RIGHT"}
LEDGE_DIRS = {1: "RIGHT", 2: "LEFT", 3: "UP", 4: "DOWN"}

WALL, WATER, LAND_ENCOUNTERS, WATER_ENCOUNTERS = 1, 2, 4, 8


class MapData:
    def __init__(self, name: str, d: dict):
        self.name = name
        self.w, self.h = d["w"], d["h"]
        self.cells = base64.b64decode(d["grid"])
        self.warps = d["warps"]  # [x, y, dest map, dest warp index (-1: dynamic)]
        self.connections = {CONNECTION_DIRS[c[0]]: (c[1], c[2]) for c in d["connections"] if c[0] in CONNECTION_DIRS}
        self.objects = d["objects"]  # [local id, x, y, script, hide flag]
        self.signs = d["signs"]  # [x, y, type, script]
        self.triggers = d["triggers"]  # [x, y, var, value, script]
        self.warp_at = {(w[0], w[1]): w for w in self.warps}

    def cell(self, x: int, y: int) -> int | None:
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.cells[y * self.w + x]
        return None

    def grass(self) -> list[tuple[int, int]]:
        return [(i % self.w, i // self.w) for i, c in enumerate(self.cells) if c & LAND_ENCOUNTERS and not c & WALL]


class World:
    def __init__(self, data: dict):
        self.maps = {name: MapData(name, d) for name, d in data["maps"].items()}

    @classmethod
    def load(cls, game_name: str) -> "World | None":
        path = GAMES / f"{game_name}.world.json.gz"
        if not path.exists():
            return None
        return cls(json.loads(gzip.decompress(path.read_bytes())))

    @cached_property
    def neighbours(self) -> dict[str, set[str]]:
        """Which maps each map leads to directly."""
        out = {}
        for name, m in self.maps.items():
            out[name] = {w[2] for w in m.warps if w[2] in self.maps} | {c[1] for c in m.connections.values()}
        return out

    def _step(self, m: MapData, x: int, y: int, d: str, surf: bool):
        """Where pressing `d` at (x, y) on map m leads: (map name, x, y), or None if it doesn't."""
        dx, dy = DIRS[d]
        nx, ny = x + dx, y + dy
        c = m.cell(nx, ny)
        if c is None:  # off the edge: a connection?
            conn = m.connections.get(d)
            if conn is None:
                return None
            offset, dest = conn
            t = self.maps.get(dest)
            if t is None:
                return None
            if d in ("UP", "DOWN"):
                tx, ty = nx - offset, (t.h - 1 if d == "UP" else 0)
            else:
                tx, ty = (t.w - 1 if d == "LEFT" else 0), ny - offset
            tc = t.cell(tx, ty)
            if tc is None or (tc & WALL and (tx, ty) not in t.warp_at):
                return None
            return dest, tx, ty
        warp = m.warp_at.get((nx, ny))
        if warp is not None:
            return self._arrive(warp) or ((m.name, nx, ny) if not c & WALL else None)
        ledge = LEDGE_DIRS.get(c >> 4 & 7)
        if c & WALL:
            if ledge == d:  # jump the ledge: land two tiles on
                lc = m.cell(nx + dx, ny + dy)
                if lc is not None and not lc & WALL and (surf or not lc & WATER):
                    return m.name, nx + dx, ny + dy
            return None
        if c & WATER and not surf:
            return None
        return m.name, nx, ny

    def _arrive(self, warp):
        dest = self.maps.get(warp[2])
        if dest is None or warp[3] < 0 or warp[3] >= len(dest.warps):
            return None
        tx, ty = dest.warps[warp[3]][:2]
        return dest.name, tx, ty

    def _exit_from_warp(self, m: MapData, x: int, y: int, d: str):
        """Standing on a warp tile (a doormat, stairs), pressing towards a wall or the edge uses it."""
        warp = m.warp_at.get((x, y))
        if warp is None:
            return None
        dx, dy = DIRS[d]
        c = m.cell(x + dx, y + dy)
        if c is None and d not in m.connections or (c is not None and c & WALL):
            return self._arrive(warp)
        return None

    def route(self, start: tuple[str, int, int], goal, surf: bool = False, avoid=frozenset(),
              blocked=frozenset(), limit: int = 300_000) -> list[tuple[str, int, int, str]] | None:
        """Shortest presses from `start` to a state where goal(map, x, y) is true.

        Returns [(map, x, y, direction)]: at (map, x, y), press direction. [] if
        already there; None if there's no way. `avoid` holds (map, x, y,
        direction) presses known not to work (people, trees, scripts);
        `blocked` holds (map, x, y) tiles not to step on unless they're the goal
        (people standing there, story gates).
        """
        if start[0] not in self.maps:
            return None
        if goal(*start):
            return []
        prev = {start: None}
        q = deque([start])
        while q and len(prev) < limit:
            cur = q.popleft()
            m = self.maps.get(cur[0])
            if m is None:
                continue
            for d in DIRS:
                if (cur[0], cur[1], cur[2], d) in avoid:
                    continue
                nxt = self._step(m, cur[1], cur[2], d, surf) or self._exit_from_warp(m, cur[1], cur[2], d)
                if nxt is None or nxt in prev:
                    continue
                reached = goal(*nxt)
                if nxt in blocked and not reached:
                    continue
                prev[nxt] = (cur, d)
                if reached:
                    path = []
                    node = nxt
                    while prev[node] is not None:
                        p, dd = prev[node]
                        path.append((p[0], p[1], p[2], dd))
                        node = p
                    return path[::-1]
                q.append(nxt)
        return None

    def adjacent_spots(self, map_name: str, x: int, y: int) -> list[tuple[int, int, str]]:
        """Tiles next to (x, y) to stand on, with the direction to face it (to talk to someone there)."""
        m = self.maps.get(map_name)
        out = []
        if m is None:
            return out
        for d, (dx, dy) in DIRS.items():
            sx, sy = x - dx, y - dy
            c = m.cell(sx, sy)
            if c is not None and not c & WALL:
                out.append((sx, sy, d))
        # Across a counter (a nurse, a clerk): two tiles away, facing them.
        for d, (dx, dy) in DIRS.items():
            sx, sy = x - 2 * dx, y - 2 * dy
            c = m.cell(sx, sy)
            mid = m.cell(x - dx, y - dy)
            if c is not None and not c & WALL and mid is not None and mid & WALL:
                out.append((sx, sy, d))
        return out
