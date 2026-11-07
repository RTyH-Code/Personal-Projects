"""Reading Pokémon FireRed's RAM.

Addresses are for FireRed (US, game code BPRE). They were checked against
pret/pokefirered, and are the same in v1.0 and v1.1: the two revisions
differ only in code and text, never in what's in RAM.

Some save offsets depend on the number of species, which the FireRed QoL +
Hard hack raises. Those come from the game profile (firered_ai/game.py,
generated from the source by tools/game_data.py). The global addresses below
hold for the hack too: its new RAM data is linked after them.

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
MAIN_HELD_KEYS_RAW = 0x28  # u16, updated by the game's main loop each frame
MAIN_IN_BATTLE = 0x439  # bit 1
SB1_POS = 0x0  # s16 x, s16 y
SB1_LOCATION = 0x4  # s8 mapGroup, s8 mapNum
SB1_MONEY = 0x290  # u32, XOR with SaveBlock2.encryptionKey
SB1_FLAGS = 0xEE0
SB1_VARS = 0x1000
NUM_FLAG_BYTES = 0x120
VARS_START = 0x4000

# Vanilla values of the offsets that move with the species count.
VANILLA_LAYOUT = {
    "dex_flag_bytes": 52,
    "sb2_dex_owned": 0x28,
    "sb2_dex_seen": 0x5C,
    "sb2_encryption_key": 0xF20,
    "sb1_bag_pockets": {"items": [0x310, 42], "key_items": [0x3B8, 30], "poke_balls": [0x430, 13],
                        "tm_hm": [0x464, 58], "berries": [0x54C, 43]},
    "dex_count": 386,
}
# Kept for older code and tests: the vanilla layout.
SB2_DEX_OWNED = VANILLA_LAYOUT["sb2_dex_owned"]
SB2_DEX_SEEN = VANILLA_LAYOUT["sb2_dex_seen"]
SB2_ENCRYPTION_KEY = VANILLA_LAYOUT["sb2_encryption_key"]
DEX_FLAG_BYTES = VANILLA_LAYOUT["dex_flag_bytes"]

FLAG_BADGE01 = 0x820  # FLAG_BADGE01_GET .. FLAG_BADGE08_GET are consecutive
FLAG_SYS_POKEMON_GET = 0x828
FLAG_SYS_POKEDEX_GET = 0x829
FLAG_SYS_GAME_CLEAR = 0x82C  # set when you enter the Hall of Fame
FLAG_SYS_NATIONAL_DEX = 0x840

BATTLE_TYPE_DOUBLE = 1 << 0
BATTLE_TYPE_TRAINER = 1 << 3

MON_SIZE = 100
BOX_PERSONALITY, BOX_OT_ID, BOX_FLAGS, BOX_CHECKSUM, BOX_SECURE = 0x00, 0x04, 0x13, 0x1C, 0x20
MON_STATUS = 0x50
MON_LEVEL = 0x54
MON_HP = 0x56
MON_MAX_HP = 0x58
MON_STATS = 0x5A  # attack, defense, speed, sp. attack, sp. defense (u16 each)

# For personality % 24: the position (0-3) of the Growth, Attacks, EVs and
# Misc substructures. Copied from GetSubstruct's SUBSTRUCT_CASE table in
# src/pokemon.c.
SUBSTRUCT_POS = [
    (0, 1, 2, 3), (0, 1, 3, 2), (0, 2, 1, 3), (0, 3, 1, 2), (0, 2, 3, 1), (0, 3, 2, 1),
    (1, 0, 2, 3), (1, 0, 3, 2), (2, 0, 1, 3), (3, 0, 1, 2), (2, 0, 3, 1), (3, 0, 2, 1),
    (1, 2, 0, 3), (1, 3, 0, 2), (2, 1, 0, 3), (3, 1, 0, 2), (2, 3, 0, 1), (3, 2, 0, 1),
    (1, 2, 3, 0), (1, 3, 2, 0), (2, 1, 3, 0), (3, 1, 2, 0), (2, 3, 1, 0), (3, 2, 1, 0),
]
# The QoL + Hard hack marks fainted Nuzlocke Pokémon with bit 0 of
# unusedRibbons (DEAD_BIT in src/hack_challenge.c): bit 27 of the Misc ribbons word.
NUZLOCKE_DEAD_BIT = 1 << 27

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
    status: int = 0
    species: int = 0
    exp: int = 0
    held_item: int = 0
    is_egg: bool = False
    bad_egg: bool = False  # the game's own "Bad Egg" flag
    checksum_ok: bool = True  # the encrypted data matches its checksum
    nuzlocke_dead: bool = False
    stats: tuple[int, ...] = ()
    raw_hp: int = 0  # current HP as stored, before clamping to max_hp
    personality: int = 0
    ot_id: int = 0
    moves: tuple[int, ...] = ()  # move numbers (0 = empty slot)
    pp: tuple[int, ...] = ()

    def is_shiny(self, odds: int = 8) -> bool:
        p, t = self.personality, self.ot_id
        return ((t >> 16) ^ (t & 0xFFFF) ^ (p >> 16) ^ (p & 0xFFFF)) < odds


@dataclass
class GameState:
    valid: bool  # False until the save blocks exist (title screen, intro)
    map_group: int = 0
    map_num: int = 0
    x: int = 0
    y: int = 0
    in_battle: bool = False
    battle_type: int = 0
    party: list[Mon] = field(default_factory=list)
    party_count: int = 0  # as the game stores it, before any sanity checks
    badges: int = 0  # bitmask, bit 0 = Boulder Badge
    money: int = 0
    raw_money: int = 0
    dex_owned: int = 0
    dex_seen: int = 0
    owned: frozenset[int] = frozenset()  # Pokédex numbers
    seen: frozenset[int] = frozenset()
    has_pokemon: bool = False
    has_pokedex: bool = False
    champion: bool = False
    national_dex: bool = False
    held_keys: int = 0  # gMain.heldKeysRaw
    flags: bytes = b""
    vars: bytes = b""  # story variables 0x4000-0x40FF
    bag: dict[str, list[tuple[int, int]]] = field(default_factory=dict)  # pocket -> [(item, quantity)]
    enemy: Mon | None = None  # the opposing lead, in battle
    enemy_party: list[Mon] = field(default_factory=list)  # the opposing team, in battle
    nuzlocke_areas: bytes = b""  # QoL + Hard: used-area bits

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
        live = [m for m in self.party if not m.is_egg]
        return bool(live) and all(m.hp == 0 for m in live)

    @property
    def trainer_battle(self) -> bool:
        return self.in_battle and bool(self.battle_type & BATTLE_TYPE_TRAINER)

    def var(self, n: int) -> int:
        i = 2 * (n - VARS_START)
        return int.from_bytes(self.vars[i : i + 2], "little") if 0 <= i < len(self.vars) - 1 else 0

    def flag(self, n: int) -> bool:
        i = n // 8
        return i < len(self.flags) and bool(self.flags[i] >> (n % 8) & 1)

    @property
    def active(self) -> "Mon | None":
        """Our Pokémon most likely in battle: the first one that can still fight."""
        return next((m for m in self.party if not m.is_egg and m.hp > 0), None)

    @property
    def active_enemy(self) -> "Mon | None":
        return next((m for m in self.enemy_party if m.hp > 0), self.enemy)

    def item_count(self, item: int) -> int:
        return sum(q for pocket in self.bag.values() for it, q in pocket if it == item)


def _u8(read: Reader, a: int) -> int:
    return read(a, 1)[0]


def _u32(read: Reader, a: int) -> int:
    return struct.unpack("<I", read(a, 4))[0]


def _dex_numbers(data: bytes, limit: int) -> frozenset[int]:
    return frozenset(n for n in (i * 8 + b + 1 for i, byte in enumerate(data) if byte for b in range(8) if byte >> b & 1)
                     if n <= limit)


def decode_mon(raw: bytes) -> Mon:
    """One 100-byte party Pokémon, with its encrypted data decrypted and checked."""
    personality, ot_id = struct.unpack_from("<II", raw, BOX_PERSONALITY)
    flags = raw[BOX_FLAGS]
    checksum = struct.unpack_from("<H", raw, BOX_CHECKSUM)[0]
    key = personality ^ ot_id
    words = struct.unpack_from("<12I", raw, BOX_SECURE)
    plain = struct.pack("<12I", *(w ^ key for w in words))
    ok = (sum(struct.unpack("<24H", plain)) & 0xFFFF) == checksum
    pos = SUBSTRUCT_POS[personality % 24]
    growth = plain[pos[0] * 12 : pos[0] * 12 + 12]
    attacks = plain[pos[1] * 12 : pos[1] * 12 + 12]
    misc = plain[pos[3] * 12 : pos[3] * 12 + 12]
    moves = struct.unpack_from("<4H", attacks)
    pp = struct.unpack_from("<4B", attacks, 8)
    species, held_item, exp = struct.unpack_from("<HHI", growth)
    ivs, ribbons = struct.unpack_from("<II", misc, 4)
    hp, max_hp = struct.unpack_from("<HH", raw, MON_HP)
    return Mon(
        level=raw[MON_LEVEL],
        hp=min(hp, max_hp),
        max_hp=max_hp,
        status=struct.unpack_from("<I", raw, MON_STATUS)[0],
        species=species,
        exp=exp,
        held_item=held_item,
        is_egg=bool(flags & 0x4) or bool(ivs >> 30 & 1),
        bad_egg=bool(flags & 0x1),
        checksum_ok=ok,
        nuzlocke_dead=bool(ribbons & NUZLOCKE_DEAD_BIT),
        stats=struct.unpack_from("<5H", raw, MON_STATS),
        raw_hp=hp,
        personality=personality,
        ot_id=ot_id,
        moves=moves,
        pp=pp,
    )


def read_state(read: Reader, addrs: dict[str, int] = DEFAULT_ADDRESSES, layout: dict | None = None) -> GameState:
    lay = {**VANILLA_LAYOUT, **(layout or {})}
    held = struct.unpack("<H", read(addrs["gMain"] + MAIN_HELD_KEYS_RAW, 2))[0]
    sb1 = _u32(read, addrs["gSaveBlock1Ptr"])
    sb2 = _u32(read, addrs["gSaveBlock2Ptr"])
    if sb1 not in EWRAM or sb2 not in EWRAM:
        return GameState(valid=False, held_keys=held)

    x, y = struct.unpack("<hh", read(sb1 + SB1_POS, 4))
    group, num = struct.unpack("<bb", read(sb1 + SB1_LOCATION, 2))

    stored_count = _u8(read, addrs["gPlayerPartyCount"])
    count = min(stored_count, 6)
    party_raw = read(addrs["gPlayerParty"], MON_SIZE * count)
    party = []
    for i in range(count):
        raw = party_raw[i * MON_SIZE : (i + 1) * MON_SIZE]
        if not any(raw[:BOX_SECURE]):  # empty slot
            continue
        party.append(decode_mon(raw))

    flags = read(sb1 + SB1_FLAGS, NUM_FLAG_BYTES)
    key = _u32(read, sb2 + lay["sb2_encryption_key"])
    raw_money = _u32(read, sb1 + SB1_MONEY) ^ key
    n = lay["dex_flag_bytes"]
    owned = _dex_numbers(read(sb2 + lay["sb2_dex_owned"], n), lay["dex_count"])
    seen = _dex_numbers(read(sb2 + lay["sb2_dex_seen"], n), lay["dex_count"])

    bag = {}
    for pocket, (off, slots) in lay["sb1_bag_pockets"].items():
        data = read(sb1 + off, 4 * slots)
        items = []
        for j in range(slots):
            item, qty = struct.unpack_from("<HH", data, 4 * j)
            if item:
                items.append((item, qty ^ (key & 0xFFFF)))
        bag[pocket] = items

    def flag(f):
        return bool(flags[f // 8] >> (f % 8) & 1)

    in_battle = bool(_u8(read, addrs["gMain"] + MAIN_IN_BATTLE) & 0x2)
    enemy = None
    enemy_party = []
    if in_battle:
        raw_all = read(addrs["gEnemyParty"], MON_SIZE * 6)
        for i in range(6):
            raw = raw_all[i * MON_SIZE : (i + 1) * MON_SIZE]
            if any(raw[:BOX_SECURE]):
                enemy_party.append(decode_mon(raw))
        enemy = enemy_party[0] if enemy_party else None
    areas = b""
    if "sb1_nuzlocke_areas" in lay:
        off, size = lay["sb1_nuzlocke_areas"]
        areas = read(sb1 + off, size)

    return GameState(
        valid=True,
        map_group=group,
        map_num=num,
        x=x,
        y=y,
        in_battle=in_battle,
        battle_type=_u32(read, addrs["gBattleTypeFlags"]),
        party=party,
        party_count=stored_count,
        badges=flags[FLAG_BADGE01 // 8],
        money=raw_money if raw_money <= 999999 else 0,
        raw_money=raw_money,
        dex_owned=len(owned),
        dex_seen=len(seen),
        owned=owned,
        seen=seen,
        has_pokemon=flag(FLAG_SYS_POKEMON_GET),
        has_pokedex=flag(FLAG_SYS_POKEDEX_GET),
        champion=flag(FLAG_SYS_GAME_CLEAR),
        national_dex=flag(FLAG_SYS_NATIONAL_DEX),
        held_keys=held,
        flags=flags,
        vars=read(sb1 + SB1_VARS, 0x200),
        bag=bag,
        enemy=enemy,
        enemy_party=enemy_party,
        nuzlocke_areas=areas,
    )


def read_var(read: Reader, var: int, addrs: dict[str, int] = DEFAULT_ADDRESSES) -> int:
    sb1 = _u32(read, addrs["gSaveBlock1Ptr"])
    if sb1 not in EWRAM:
        return 0
    return struct.unpack("<H", read(sb1 + SB1_VARS + 2 * (var - VARS_START), 2))[0]
