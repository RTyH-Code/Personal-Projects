"""Reading Pokémon FireRed's RAM.

Addresses are for FireRed (US, rev 0, game code BPRE). They were checked
against pret/pokefirered. They also hold for the FireRed QoL + Hard hack in
this repo, because every symbol used here is linked before the hack's only
new EWRAM data.

If you play a different hack, generate an address file from its linker map:
    python tools/symbols_from_map.py pokefirered.map > addresses.json
and pass it with --addresses.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from typing import Callable

Reader = Callable[[int, int], bytes]  # (address, size) -> bytes

DEFAULT_ADDRESSES = {
    "gMain": 0x030030F0,
    "gSaveBlock1Ptr": 0x03005008,
    "gSaveBlock2Ptr": 0x0300500C,
    "gPlayerPartyCount": 0x02024029,
    "gPlayerParty": 0x02024284,
    "gEnemyParty": 0x0202402C,
    "gBattleTypeFlags": 0x02022B4C,
}

# Offsets inside structs (include/global.h, include/main.h, include/pokemon.h).
MAIN_IN_BATTLE = 0x439  # bit 1
SB1_POS = 0x0  # s16 x, s16 y
SB1_LOCATION = 0x4  # s8 mapGroup, s8 mapNum
SB1_MONEY = 0x290  # u32, XOR with SaveBlock2.encryptionKey
SB1_FLAGS = 0xEE0
SB2_DEX_OWNED = 0x18 + 0x10
SB2_DEX_SEEN = 0x18 + 0x44
SB2_ENCRYPTION_KEY = 0xF20
DEX_FLAG_BYTES = 52

FLAG_BADGE01 = 0x820  # FLAG_BADGE01_GET .. FLAG_BADGE08_GET are consecutive
FLAG_SYS_POKEMON_GET = 0x828
FLAG_SYS_POKEDEX_GET = 0x829
FLAG_SYS_GAME_CLEAR = 0x82C  # set when you enter the Hall of Fame
FLAG_SYS_NATIONAL_DEX = 0x840

MON_SIZE = 100
MON_STATUS = 0x50
MON_LEVEL = 0x54
MON_HP = 0x56
MON_MAX_HP = 0x58

EWRAM = range(0x02000000, 0x02040000)


def load_addresses(path: str | None) -> dict[str, int]:
    addrs = dict(DEFAULT_ADDRESSES)
    if path:
        with open(path) as f:
            for k, v in json.load(f).items():
                addrs[k] = int(v, 0) if isinstance(v, str) else int(v)
    return addrs


@dataclass
class Mon:
    level: int
    hp: int
    max_hp: int
    status: int


@dataclass
class GameState:
    valid: bool  # False until the save blocks exist (title screen, intro)
    map_group: int = 0
    map_num: int = 0
    x: int = 0
    y: int = 0
    in_battle: bool = False
    party: list[Mon] = field(default_factory=list)
    badges: int = 0  # bitmask, bit 0 = Boulder Badge
    money: int = 0
    dex_owned: int = 0
    dex_seen: int = 0
    owned: frozenset[int] = frozenset()  # national dex numbers
    has_pokemon: bool = False
    has_pokedex: bool = False
    champion: bool = False
    national_dex: bool = False

    @property
    def map_id(self) -> tuple[int, int]:
        return (self.map_group, self.map_num)

    @property
    def badge_count(self) -> int:
        return bin(self.badges).count("1")

    @property
    def level_sum(self) -> int:
        return sum(m.level for m in self.party)

    @property
    def hp_fraction(self) -> float:
        max_hp = sum(m.max_hp for m in self.party)
        return sum(m.hp for m in self.party) / max_hp if max_hp else 0.0

    @property
    def all_fainted(self) -> bool:
        return bool(self.party) and all(m.hp == 0 for m in self.party)


def _u8(read: Reader, a: int) -> int:
    return read(a, 1)[0]


def _u32(read: Reader, a: int) -> int:
    return struct.unpack("<I", read(a, 4))[0]


def _flag(flags: bytes, flag: int) -> bool:
    i = flag // 8 - FLAG_BADGE01 // 8
    return bool(flags[i] >> (flag % 8) & 1)


def _dex_numbers(data: bytes) -> frozenset[int]:
    return frozenset(i * 8 + b + 1 for i, byte in enumerate(data) if byte for b in range(8) if byte >> b & 1)


def read_state(read: Reader, addrs: dict[str, int] = DEFAULT_ADDRESSES) -> GameState:
    sb1 = _u32(read, addrs["gSaveBlock1Ptr"])
    sb2 = _u32(read, addrs["gSaveBlock2Ptr"])
    if sb1 not in EWRAM or sb2 not in EWRAM:
        return GameState(valid=False)

    x, y = struct.unpack("<hh", read(sb1 + SB1_POS, 4))
    group, num = struct.unpack("<bb", read(sb1 + SB1_LOCATION, 2))

    count = min(_u8(read, addrs["gPlayerPartyCount"]), 6)
    party_raw = read(addrs["gPlayerParty"], MON_SIZE * count)
    party = []
    for i in range(count):
        o = i * MON_SIZE
        status = struct.unpack_from("<I", party_raw, o + MON_STATUS)[0]
        level = party_raw[o + MON_LEVEL]
        hp, max_hp = struct.unpack_from("<HH", party_raw, o + MON_HP)
        if max_hp == 0:  # empty or corrupt slot
            continue
        party.append(Mon(level, min(hp, max_hp), max_hp, status))

    flags = read(sb1 + SB1_FLAGS + FLAG_BADGE01 // 8, 5)
    key = _u32(read, sb2 + SB2_ENCRYPTION_KEY)
    money = _u32(read, sb1 + SB1_MONEY) ^ key
    owned = frozenset(n for n in _dex_numbers(read(sb2 + SB2_DEX_OWNED, DEX_FLAG_BYTES)) if n <= 386)

    return GameState(
        valid=True,
        map_group=group,
        map_num=num,
        x=x,
        y=y,
        in_battle=bool(_u8(read, addrs["gMain"] + MAIN_IN_BATTLE) & 0x2),
        party=party,
        badges=flags[0],
        money=money if money <= 999999 else 0,
        dex_owned=len(owned),
        dex_seen=len(_dex_numbers(read(sb2 + SB2_DEX_SEEN, DEX_FLAG_BYTES))),
        owned=owned,
        has_pokemon=_flag(flags, FLAG_SYS_POKEMON_GET),
        has_pokedex=_flag(flags, FLAG_SYS_POKEDEX_GET),
        champion=_flag(flags, FLAG_SYS_GAME_CLEAR),
        national_dex=_flag(flags, FLAG_SYS_NATIONAL_DEX),
    )
