"""Gen 4 Pokemon data, as the game keeps it in RAM: decode, edit and encode.

A party Pokemon is 236 bytes: the personality value (PID), flags and a
checksum, four 32-byte blocks (A: species, item, trainer IDs, experience,
friendship, ability, EVs; B: moves, PP, IVs; C: nickname; D: trainer name,
dates, places, ball) stored in an order the PID picks and encrypted with a
generator seeded by the checksum, then 100 bytes of battle stats encrypted
with one seeded by the PID. The checksum is the sum of the blocks' 16-bit
words.
"""
import struct

ORDERS = ["ABCD", "ABDC", "ACBD", "ACDB", "ADBC", "ADCB", "BACD", "BADC", "BCAD", "BCDA", "BDAC", "BDCA",
          "CABD", "CADB", "CBAD", "CBDA", "CDAB", "CDBA", "DABC", "DACB", "DBAC", "DBCA", "DCAB", "DCBA"]
PARTY_SIZE = 236


def _crypt(data, seed):
    out = bytearray(data)
    x = seed
    for i in range(0, len(out), 2):
        x = (x * 0x41C64E6D + 0x6073) & 0xFFFFFFFF
        w = struct.unpack_from("<H", out, i)[0] ^ (x >> 16)
        struct.pack_into("<H", out, i, w)
    return bytes(out)


class Mon:
    """A decoded party Pokemon. `blocks` holds A, B, C and D in that order (128 bytes), `stats` the battle stats."""

    def __init__(self, raw):
        self.pid, self.flags, self.checksum = struct.unpack_from("<IHH", raw, 0)
        shuffled = _crypt(raw[8:136], self.checksum)
        order = ORDERS[((self.pid >> 13) & 31) % 24]
        parts = {order[i]: shuffled[32 * i:32 * i + 32] for i in range(4)}
        self.blocks = bytearray(b"".join(parts[k] for k in "ABCD"))
        self.stats = bytearray(_crypt(raw[136:236], self.pid)) if len(raw) >= 236 else bytearray(100)

    def valid(self):
        return sum(struct.unpack("<64H", bytes(self.blocks))) & 0xFFFF == self.checksum

    def encode(self):
        self.checksum = sum(struct.unpack("<64H", bytes(self.blocks))) & 0xFFFF
        order = ORDERS[((self.pid >> 13) & 31) % 24]
        parts = {k: bytes(self.blocks[32 * i:32 * i + 32]) for i, k in enumerate("ABCD")}
        shuffled = b"".join(parts[k] for k in order)
        return (struct.pack("<IHH", self.pid, self.flags, self.checksum) + _crypt(shuffled, self.checksum)
                + _crypt(bytes(self.stats), self.pid))

    # block offsets below are from the start of block A (byte 8 of the Pokemon)
    def u16(self, at):
        return struct.unpack_from("<H", self.blocks, at)[0]

    def set_u16(self, at, v):
        struct.pack_into("<H", self.blocks, at, v)

    def u32(self, at):
        return struct.unpack_from("<I", self.blocks, at)[0]

    def set_u32(self, at, v):
        struct.pack_into("<I", self.blocks, at, v)

    @property
    def species(self):
        return self.u16(0x00)

    @property
    def is_egg(self):
        return bool(self.u32(0x30) >> 30 & 1)

    @property
    def level(self):
        return self.stats[4]
