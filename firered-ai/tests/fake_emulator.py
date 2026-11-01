"""A stand-in for the emulator that fakes FireRed's RAM, so tests need no ROM."""

import pickle
import struct

import numpy as np

from firered_ai import ram

SB1 = 0x0202552C
SB2 = 0x02024588
KEY = 0x12345678


class FakeEmulator:
    def __init__(self, valid=True):
        self.mem = {0x02000000: bytearray(0x40000), 0x03000000: bytearray(0x8000)}
        self.frame = 0
        self.presses = []
        if valid:
            self.w32(ram.DEFAULT_ADDRESSES["gSaveBlock1Ptr"], SB1)
            self.w32(ram.DEFAULT_ADDRESSES["gSaveBlock2Ptr"], SB2)
            self.w32(SB2 + ram.SB2_ENCRYPTION_KEY, KEY)
            self.set_map(4, 1)
            self.set_pos(5, 5)

    # --- RAM helpers ----------------------------------------------------
    def _loc(self, a):
        for base, buf in self.mem.items():
            if base <= a < base + len(buf):
                return buf, a - base
        raise ValueError(hex(a))

    def write(self, a, data):
        buf, o = self._loc(a)
        buf[o : o + len(data)] = data

    def w32(self, a, v):
        self.write(a, struct.pack("<I", v))

    def set_map(self, group, num):
        self.write(SB1 + ram.SB1_LOCATION, struct.pack("<bb", group, num))

    def set_pos(self, x, y):
        self.write(SB1 + ram.SB1_POS, struct.pack("<hh", x, y))

    def pos(self):
        return struct.unpack("<hh", self.read(SB1 + ram.SB1_POS, 4))

    def set_party(self, mons):  # [(level, hp, max_hp)]
        self.write(ram.DEFAULT_ADDRESSES["gPlayerPartyCount"], bytes([len(mons)]))
        for i, (lv, hp, mx) in enumerate(mons):
            base = ram.DEFAULT_ADDRESSES["gPlayerParty"] + i * ram.MON_SIZE
            self.write(base + ram.MON_LEVEL, bytes([lv]))
            self.write(base + ram.MON_HP, struct.pack("<HH", hp, mx))

    def set_flag(self, flag, on=True):
        a = SB1 + ram.SB1_FLAGS + flag // 8
        b = self.read(a, 1)[0]
        b = b | (1 << (flag % 8)) if on else b & ~(1 << (flag % 8))
        self.write(a, bytes([b]))

    def set_owned(self, n):
        self.write(SB2 + ram.SB2_DEX_OWNED, b"\xff" * (n // 8) + bytes([(1 << (n % 8)) - 1]))

    def set_money(self, m):
        self.w32(SB1 + ram.SB1_MONEY, m ^ KEY)

    def set_in_battle(self, on):
        self.write(ram.DEFAULT_ADDRESSES["gMain"] + ram.MAIN_IN_BATTLE, bytes([0x2 if on else 0]))

    # --- emulator interface ----------------------------------------------
    def read(self, a, size):
        buf, o = self._loc(a)
        return bytes(buf[o : o + size])

    def press(self, buttons, frames):
        self.frame += frames
        if buttons:
            self.presses.append(buttons)
        x, y = self.pos()
        moves = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
        for b in buttons:
            if b in moves:
                self.set_pos(x + moves[b][0], y + moves[b][1])

    def screen(self):
        return np.full((160, 240, 3), self.frame % 256, np.uint8)

    def save_state(self):
        return pickle.dumps((self.mem, self.frame))

    def load_state(self, s):
        self.mem, self.frame = pickle.loads(s)

    def close(self):
        pass
