"""A stand-in for the emulator that fakes FireRed's RAM, so tests need no ROM."""

import pickle
import struct

import numpy as np

from firered_ai import ram

SB1 = 0x0202552C
SB2 = 0x02024588
KEY = 0x12345678


def encode_mon(level=5, hp=20, max_hp=20, species=1, exp=135, personality=1000, ot_id=0x1234ABCD,
               held_item=0, nuzlocke_dead=False, is_egg=False, bad_checksum=False, stats=(10, 10, 10, 10, 10)):
    """A 100-byte party Pokémon, encrypted the way the game stores it."""
    growth = struct.pack("<HHIBB2x", species, held_item, exp, 0, 70)
    attacks = struct.pack("<4H4B", 33, 0, 0, 0, 35, 0, 0, 0)
    evs = bytes(12)
    ribbons = ram.NUZLOCKE_DEAD_BIT if nuzlocke_dead else 0
    misc = struct.pack("<BBHII", 0, 0, 0, (1 << 30) if is_egg else 0, ribbons)
    subs = [growth, attacks, evs, misc]
    pos = ram.SUBSTRUCT_POS[personality % 24]
    plain = bytearray(48)
    for kind, data in enumerate(subs):
        plain[pos[kind] * 12 : pos[kind] * 12 + 12] = data
    checksum = sum(struct.unpack("<24H", plain)) & 0xFFFF
    if bad_checksum:
        checksum ^= 0x5555
    key = personality ^ ot_id
    secure = struct.pack("<12I", *(w ^ key for w in struct.unpack("<12I", plain)))
    raw = bytearray(100)
    struct.pack_into("<II", raw, 0, personality, ot_id)
    raw[8:18] = b"\xbb" * 10  # nickname "AAAAAAAAAA"
    raw[ram.BOX_FLAGS] = 0x2 | (0x4 if is_egg else 0)  # hasSpecies
    struct.pack_into("<H", raw, ram.BOX_CHECKSUM, checksum)
    raw[ram.BOX_SECURE : ram.BOX_SECURE + 48] = secure
    raw[ram.MON_LEVEL] = level
    struct.pack_into("<HH5H", raw, ram.MON_HP, hp, max_hp, *stats)
    return bytes(raw)


class FakeEmulator:
    def __init__(self, valid=True):
        self.mem = {0x02000000: bytearray(0x40000), 0x03000000: bytearray(0x8000)}
        self.frame = 0
        self.presses = []
        if valid:
            self.w32(ram.DEFAULT_ADDRESSES["gSaveBlock1Ptr"], SB1)
            self.w32(ram.DEFAULT_ADDRESSES["gSaveBlock2Ptr"], SB2)
            self.w32(SB2 + ram.SB2_ENCRYPTION_KEY, KEY)
            self.w32(SB2 + ram.SB2_ENCRYPTION_KEY + 4, KEY)  # where the QoL + Hard layout has it
            self.set_map(4, 1)
            self.set_pos(5, 5)
            self.set_money(0)

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

    def set_party(self, mons):
        """mons: (level, hp, max_hp) tuples, or dicts of encode_mon arguments."""
        self.write(ram.DEFAULT_ADDRESSES["gPlayerPartyCount"], bytes([len(mons)]))
        for i, m in enumerate(mons):
            if not isinstance(m, dict):
                m = dict(zip(("level", "hp", "max_hp"), m))
            self.write(ram.DEFAULT_ADDRESSES["gPlayerParty"] + i * ram.MON_SIZE, encode_mon(personality=1000 + i, **m))

    def party_slot(self, i):
        return ram.DEFAULT_ADDRESSES["gPlayerParty"] + i * ram.MON_SIZE

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

    # A tiny world for the explorer: walls and warps per map; None means open everywhere.
    walls = None  # set of (group, num, x, y) you can't stand on
    bounds = None  # (w, h): tiles outside 0..w-1, 0..h-1 are walls too
    warps = {}  # (group, num, x, y) -> (group, num, x, y)
    crashed = False  # the main loop stopped: heldKeysRaw no longer follows the buttons
    frozen_screen = False

    def location(self):
        g, n = struct.unpack("<bb", self.read(SB1 + ram.SB1_LOCATION, 2))
        return g, n

    def press(self, buttons, frames):
        self.frame += frames
        if buttons:
            self.presses.append(buttons)
        if not self.crashed:
            mask = sum(1 << {"A": 0, "B": 1, "SELECT": 2, "START": 3, "RIGHT": 4, "LEFT": 5, "UP": 6,
                             "DOWN": 7, "R": 8, "L": 9}[b] for b in buttons)
            self.write(ram.DEFAULT_ADDRESSES["gMain"] + ram.MAIN_HELD_KEYS_RAW, struct.pack("<H", mask))
        x, y = self.pos()
        moves = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
        for b in buttons:
            if b in moves and not self.crashed:
                nx, ny = x + moves[b][0], y + moves[b][1]
                g, n = self.location()
                if self.walls is not None and (g, n, nx, ny) in self.walls:
                    continue  # walls win, even over a warp (a person standing in a doorway)
                if (g, n, nx, ny) in self.warps:
                    g2, n2, x2, y2 = self.warps[(g, n, nx, ny)]
                    self.set_map(g2, n2)
                    self.set_pos(x2, y2)
                    continue
                if self.bounds and not (0 <= nx < self.bounds[0] and 0 <= ny < self.bounds[1]):
                    continue
                if self.walls is not None and (g, n, nx, ny) in self.walls:
                    continue
                self.set_pos(nx, ny)

    def screen(self):
        if self.frozen_screen:
            return np.zeros((160, 240, 3), np.uint8)
        return np.full((160, 240, 3), self.frame % 256, np.uint8)

    def save_state(self):
        return pickle.dumps((self.mem, self.frame))

    def load_state(self, s):
        self.mem, self.frame = pickle.loads(s)

    def close(self):
        pass
