"""End-to-end tests on the real mGBA core, using a tiny generated GBA ROM.

The ROM (hand-assembled ARM below) copies a FireRed-shaped RAM image into
EWRAM/IWRAM, then loops forever: it stores the held buttons in
gMain.heldKeysRaw (as FireRed's ReadKeys does), ORs them into the player's
y coordinate, and copies the save chip's first byte into RAM. That checks
memory reads, button presses, save states and battery saves without needing
a copy of FireRed.
"""

import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

pytest.importorskip("stable_retro")

from fake_emulator import SB1, FakeEmulator  # noqa: E402

from firered_ai import ram  # noqa: E402
from firered_ai.emulator import Emulator  # noqa: E402
from firered_ai.env import FireRedEnv  # noqa: E402

ROM_BASE = 0x08000000
CODE = 0xC0
KEYINPUT = 0x04000130
KEY_RIGHT = 1 << 4
FLASH_COPY = 0x0203FF00  # where the test ROM copies the save chip's first byte


def _branch(cond, at, target):
    return cond << 28 | 0x0A000000 | (((target - (at + 8)) >> 2) & 0xFFFFFF)


def build_rom(fake: FakeEmulator) -> bytes:
    # Copy table: (dest, src, length) for each nonzero run of fake RAM.
    runs = []
    for base, buf in fake.mem.items():
        i = 0
        while i < len(buf):
            if buf[i]:
                j = i
                while j < len(buf) and any(buf[j : j + 16]):
                    j += 16
                runs.append((base + i, bytes(buf[i:j])))
                i = j
            else:
                i += 1

    code = [None] * 28
    lit = CODE + 4 * len(code)  # literal pool: table, KEYINPUT, &y, &gMain.heldKeysRaw, FLASH_COPY
    table = lit + 20
    blob = table + 12 * len(runs) + 4
    entries, data = b"", b""
    for dest, chunk in runs:
        entries += struct.pack("<III", dest, ROM_BASE + blob + len(data), len(chunk))
        data += chunk
    entries += b"\0\0\0\0"

    def ldr_pc(i, rd, addr):
        return 0xE59F0000 | rd << 12 | (addr - (CODE + 4 * i + 8))

    code[0] = ldr_pc(0, 4, lit)  # r4 = table
    entry = CODE + 4 * 1
    code[1] = 0xE4940004  # ldr r0, [r4], #4   (dest)
    code[2] = 0xE3500000  # cmp r0, #0
    done = CODE + 4 * 11
    code[3] = _branch(0x0, CODE + 12, done)  # beq done
    code[4] = 0xE4941004  # ldr r1, [r4], #4   (src)
    code[5] = 0xE4942004  # ldr r2, [r4], #4   (len)
    copy = CODE + 4 * 6
    code[6] = 0xE4D13001  # ldrb r3, [r1], #1
    code[7] = 0xE4C03001  # strb r3, [r0], #1
    code[8] = 0xE2522001  # subs r2, r2, #1
    code[9] = _branch(0x1, CODE + 36, copy)  # bne copy
    code[10] = _branch(0xE, CODE + 40, entry)  # b entry
    # done:
    code[11] = ldr_pc(11, 5, lit + 4)  # r5 = KEYINPUT
    code[12] = ldr_pc(12, 6, lit + 8)  # r6 = &y
    code[13] = ldr_pc(13, 9, lit + 12)  # r9 = &gMain.heldKeysRaw
    code[14] = 0xE3A0A40E  # mov r10, #0x0E000000 (flash)
    code[15] = ldr_pc(15, 11, lit + 16)  # r11 = FLASH_COPY
    loop = CODE + 4 * 16
    code[16] = 0xE1D530B0  # ldrh r3, [r5]
    code[17] = 0xE1E03003  # mvn r3, r3          (keys are active low)
    code[18] = 0xE20330FF  # and r3, r3, #0xff
    code[19] = 0xE1C930B0  # strh r3, [r9]       (like the game's ReadKeys)
    code[20] = 0xE1D670B0  # ldrh r7, [r6]
    code[21] = 0xE1877003  # orr r7, r7, r3
    code[22] = 0xE1C670B0  # strh r7, [r6]
    code[23] = 0xE5DA2000  # ldrb r2, [r10]      (first byte of the save chip)
    code[24] = 0xE5CB2000  # strb r2, [r11]
    code[25] = _branch(0xE, CODE + 100, loop)  # b loop
    code[26] = code[27] = 0xE1A00000  # nop

    rom = bytearray(blob + len(data))
    struct.pack_into("<I", rom, 0, _branch(0xE, 0, CODE))
    rom[0xA0:0xAC] = b"FRAITEST\0\0\0\0"
    rom[0xB2] = 0x96
    rom[0xBD] = (-sum(rom[0xA0:0xBD]) - 0x19) & 0xFF
    for i, c in enumerate(code):
        struct.pack_into("<I", rom, CODE + 4 * i, c)
    struct.pack_into("<IIIII", rom, lit, ROM_BASE + table, KEYINPUT, SB1 + ram.SB1_POS + 2,
                     ram.DEFAULT_ADDRESSES["gMain"] + ram.MAIN_HELD_KEYS_RAW, FLASH_COPY)
    rom[table : table + len(entries)] = entries
    rom[blob:] = data
    return bytes(rom)


@pytest.fixture(scope="module")
def emu(tmp_path_factory):
    fake = FakeEmulator()
    fake.set_pos(7, 0)
    fake.set_party([(5, 19, 20), (9, 30, 31)])
    fake.set_flag(ram.FLAG_BADGE01)
    fake.set_flag(ram.FLAG_SYS_POKEMON_GET)
    fake.set_owned(3)
    fake.set_money(1234)
    d = tmp_path_factory.mktemp("rom")
    rom = d / "test.gba"
    rom.write_bytes(build_rom(fake))
    e = Emulator(str(rom), cache_dir=d / "cache")
    e.press((), 30)
    yield e
    e.close()


def test_reads_game_state(emu):
    s = ram.read_state(emu.read)
    assert s.valid
    assert s.map_id == (4, 1) and s.x == 7
    assert [(m.level, m.hp, m.max_hp) for m in s.party] == [(5, 19, 20), (9, 30, 31)]
    assert s.badges == 1 and s.has_pokemon and s.dex_owned == 3 and s.money == 1234
    assert emu.screen().shape == (160, 240, 3)


def test_buttons_and_save_states(emu):
    before = emu.save_state()
    assert ram.read_state(emu.read).y == 0
    emu.press(("RIGHT",), 4)
    emu.press((), 4)
    assert ram.read_state(emu.read).y == KEY_RIGHT
    emu.load_state(before)
    assert ram.read_state(emu.read).y == 0


def test_env_on_real_emulator(emu):
    env = FireRedEnv(emulator=emu, max_steps=5)
    obs, info = env.reset()
    assert info["map"] == "PalletTown_PlayersHouse_2F"
    for a in range(5):
        obs, r, term, trunc, info = env.step(a)
        assert env.observation_space.contains(obs)
    assert trunc


def test_held_keys_reach_gmain(emu):
    emu.press(("B",), 4)
    assert ram.read_state(emu.read).held_keys == 1 << 1
    emu.press((), 4)
    assert ram.read_state(emu.read).held_keys == 0


def test_boot_with_save(emu):
    sav = bytes([0x5A]) + bytes(range(256)) * 511
    emu.boot_with_save(sav)
    emu.press((), 10)
    assert emu.read(FLASH_COPY, 1) == b"\x5a"
    assert emu.read(0x0E000000, 4) == sav[:4]
    emu.boot_with_save(b"\x77")
    emu.press((), 10)
    assert emu.read(FLASH_COPY, 1) == b"\x77"


def test_playtest_session_on_real_emulator(emu, tmp_path):
    """A healthy game must not raise false alarms, and a session must run end to end."""
    from firered_ai.game import Game
    from firered_ai.tester import Start, Tester

    emu.boot_with_save(b"")
    start = Start("state", "tiny", emu.save_state())
    t = Tester(emu, Game.load("firered"), tmp_path, seed=5, log=None)
    found = t.session(start, 300)
    assert found == [], [(f.check, f.title) for f in found]
    assert t.stats.steps == 300
