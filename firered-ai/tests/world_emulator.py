"""A fake emulator whose player walks the real world map (firered_ai/data/games/*.world.json.gz).

Walls, water, ledges, warps and connections come from the world data, and
people stand where the map puts them (unless their hide flag is set), so the
explorer's story navigation can be tested without a ROM. Talking does
nothing unless a test hooks `on_talk`.
"""

from __future__ import annotations

import struct

from fake_emulator import SB1, FakeEmulator

from firered_ai import ram
from firered_ai.world import DIRS, World


class WorldEmulator(FakeEmulator):
    def __init__(self, game, start=("PalletTown_PlayersHouse_2F", 5, 5)):
        super().__init__()
        self.game = game
        self.world = World.load(game.name)
        self.ids = {m["name"]: k for k, m in game.maps.items()}
        self.names = {k: m["name"] for k, m in game.maps.items()}
        self.facing = "DOWN"
        self.on_talk = None  # f(emu, map name, x, y) when A is pressed facing (x, y)
        self.talks = []
        self.teleport(*start)

    def teleport(self, name, x, y):
        self.set_map(*self.ids[name])
        self.set_pos(x, y)

    def where(self):
        return self.names[self.location()], *self.pos()

    def set_var(self, name, value):
        n = self.game.vars[name] - 0x4000
        self.write(SB1 + ram.SB1_VARS + 2 * n, struct.pack("<H", value))

    def flag_on(self, name):
        n = self.game.flags[name]
        return bool(self.read(SB1 + ram.SB1_FLAGS + n // 8, 1)[0] >> (n % 8) & 1)

    def _person_at(self, name, x, y):
        for o in self.world.maps[name].objects:
            hide = o[4]
            if (o[1], o[2]) == (x, y) and not (hide != "0" and not hide.startswith("FLAG_TEMP_")
                                              and self.flag_on(hide.removeprefix("FLAG_"))):
                return o
        return None

    def press(self, buttons, frames):
        self.frame += frames
        if buttons:
            self.presses.append(buttons)
        mask = sum(1 << {"A": 0, "B": 1, "SELECT": 2, "START": 3, "RIGHT": 4, "LEFT": 5, "UP": 6,
                         "DOWN": 7, "R": 8, "L": 9}[b] for b in buttons)
        self.write(ram.DEFAULT_ADDRESSES["gMain"] + ram.MAIN_HELD_KEYS_RAW, struct.pack("<H", mask))
        name, x, y = self.where()
        m = self.world.maps[name]
        for b in buttons:
            if b == "A":
                dx, dy = DIRS[self.facing]
                self.talks.append((name, x, y, self.facing))
                if self.on_talk:
                    self.on_talk(self, name, x + dx, y + dy)
            if b not in DIRS:
                continue
            self.facing = b
            dx, dy = DIRS[b]
            if self._person_at(name, x + dx, y + dy):
                continue
            nxt = self.world._step(m, x, y, b, surf=False) or self.world._exit_from_warp(m, x, y, b)
            if nxt is not None:
                self.teleport(*nxt)
