import json
import os
import random
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fake_emulator import SB1, FakeEmulator, encode_mon  # noqa: E402

from firered_ai import ram  # noqa: E402
from firered_ai.detectors import FROZEN_STEPS, HANG_STEPS, STUCK_STEPS, Detectors  # noqa: E402
from firered_ai.explorer import Explorer  # noqa: E402
from firered_ai.game import Game  # noqa: E402
from firered_ai.report import write_report  # noqa: E402
from firered_ai.runner import pick_start  # noqa: E402
from firered_ai.tester import Start, Tester  # noqa: E402

VANILLA = Game.load("firered")
HACK = Game.load("firered_qol_hard")


def state(emu, game=VANILLA):
    return ram.read_state(emu.read, layout=game.layout)


def run_checks(det, emu, n, buttons=("A",), game=VANILLA, screen=None, **kw):
    out = []
    for i in range(n):
        emu.press(buttons, 8)
        out += det.check(state(emu, game), buttons, screen if screen is not None else i, step=i, **kw)
    return out


def kinds(findings):
    return [(f.kind, f.check, f.title) for f in findings]


# --- detectors -------------------------------------------------------------------------

def test_healthy_play_finds_nothing():
    emu = FakeEmulator()
    emu.set_party([(10, 30, 30), (12, 0, 33)])
    emu.set_money(5000)
    assert run_checks(Detectors(VANILLA), emu, 200) == []


def test_hang_when_buttons_stop_registering():
    emu = FakeEmulator()
    det = Detectors(VANILLA)
    assert run_checks(det, emu, 10) == []
    emu.crashed = True  # heldKeysRaw is stuck on A, the last button pressed
    found = []
    for i in range(HANG_STEPS * 2):
        b = (["A", "B", "UP", "A"][i % 4],)
        emu.press(b, 8)
        found += det.check(state(emu), b, i, step=i)
    assert found and set(kinds(found)) == {("crash", "hang", "The game stopped responding to buttons")}
    assert found[0].fatal and found[0].step < HANG_STEPS + 5
    # Pressing the same button the whole time is normal: held always matches.
    emu.crashed = False
    assert run_checks(Detectors(VANILLA), emu, HANG_STEPS * 2, buttons=("A",)) == []


def test_frozen_screen_and_stuck_player():
    emu = FakeEmulator()
    found = run_checks(Detectors(VANILLA), emu, FROZEN_STEPS + 1, screen=123)
    assert ("softlock", "frozen", "The screen stopped changing") in kinds(found)
    det = Detectors(VANILLA)
    found = []
    for i in range(STUCK_STEPS + 1):
        found += det.check(state(emu), ("A",), i, emu.read(ram.DEFAULT_ADDRESSES["gMain"] + ram.MAIN_HELD_KEYS_RAW, 2)[0] or 1)
    assert ("softlock", "stuck", "The player couldn't move for a long time") in kinds(found)


def test_corrupt_party_needs_two_steps():
    emu = FakeEmulator()
    emu.set_party([dict(level=9, bad_checksum=True)])
    det = Detectors(VANILLA)
    emu.press(("A",), 8)
    assert det.check(state(emu), ("A",), 1) == []  # once could be a mid-update read
    emu.press(("A",), 8)
    found = det.check(state(emu), ("A",), 2)
    assert kinds(found) == [("corrupt", "party", "Bad Egg / corrupt Pokémon data")]
    assert "Party slot 1" in found[0].detail


@pytest.mark.parametrize("mon,title", [
    (dict(hp=50, max_hp=40), "HP above max"),
    (dict(exp=0xFFFFFF00), "Exp. overflow"),
    (dict(level=0), "Level out of range"),
    (dict(species=1000), "Invalid species"),
    (dict(stats=(10, 0, 10, 10, 10)), "Zero stat"),
])
def test_impossible_pokemon(mon, title):
    emu = FakeEmulator()
    emu.set_party([mon])
    assert ("corrupt", "party", title) in kinds(run_checks(Detectors(VANILLA), emu, 3))


def test_eggs_are_not_checked_like_pokemon():
    emu = FakeEmulator()
    emu.set_party([dict(is_egg=True, level=0, max_hp=0, hp=0)])
    assert run_checks(Detectors(VANILLA), emu, 3) == []


def test_money_bag_and_map():
    emu = FakeEmulator()
    emu.set_money(1_200_000)
    key = ram.read_state(emu.read).raw_money ^ 1_200_000  # unused, just to read once
    pocket = VANILLA.layout["sb1_bag_pockets"]["items"][0]
    enc = struct.unpack("<I", emu.read(0x02024588 + ram.SB2_ENCRYPTION_KEY, 4))[0] & 0xFFFF
    emu.write(SB1 + pocket, struct.pack("<HH", 9999, 3 ^ enc))
    emu.set_map(40, 99)
    found = kinds(run_checks(Detectors(VANILLA), emu, 3))
    assert ("corrupt", "money", "Money over the limit") in found
    assert ("corrupt", "bag", "Bad bag slot") in found
    assert ("corrupt", "map", "Unknown map") in found
    del key


def test_wrong_save_layout_is_reported_once_not_flooded():
    emu = FakeEmulator()
    emu.w32(0x02024588 + ram.SB2_ENCRYPTION_KEY, 0)  # the key isn't where the profile says
    emu.w32(0x02024588 + ram.SB2_ENCRYPTION_KEY + 4, 0)
    pocket = VANILLA.layout["sb1_bag_pockets"]["items"][0]
    emu.write(SB1 + pocket, struct.pack("<HH", 13, 0x5678 ^ 3))  # 3 Potions, encrypted with the real key
    found = kinds(run_checks(Detectors(VANILLA), emu, 5))
    assert found == [("setup", "layout", "The save layout doesn't match this ROM")]


def test_level_and_exp_never_go_down():
    emu = FakeEmulator()
    emu.set_party([dict(level=20, exp=8000)])
    det = Detectors(VANILLA)
    assert run_checks(det, emu, 2) == []
    emu.set_party([dict(level=20, exp=7000)])
    assert ("corrupt", "progress", "Level or Exp. went down") in kinds(run_checks(det, emu, 2))


def test_level_cap():
    emu = FakeEmulator()
    emu.set_flag(HACK.flags["HACK_LEVEL_CAP"])
    emu.set_party([dict(level=15)])
    det = Detectors(HACK)
    assert HACK.level_cap(state(emu, HACK)) == 16
    run_checks(det, emu, 2, game=HACK)
    emu.set_party([dict(level=16)])
    assert run_checks(det, emu, 2, game=HACK) == []  # up to the cap is fine
    emu.set_party([dict(level=17)])
    found = run_checks(det, emu, 2, game=HACK)
    assert kinds(found) == [("rule", "level_cap", "Leveled past the level cap")]
    emu.set_flag(HACK.flags["BADGE01_GET"])  # Brock beaten: the cap is Misty's
    assert HACK.level_cap(state(emu, HACK)) == 23


def test_nuzlocke_fainted_pokemon_stays_fainted():
    emu = FakeEmulator()
    emu.set_flag(HACK.flags["HACK_NUZLOCKE"])
    emu.set_flag(ram.FLAG_SYS_POKEDEX_GET)
    emu.set_party([dict(nuzlocke_dead=True, hp=0)])
    det = Detectors(HACK)
    assert run_checks(det, emu, 3, game=HACK) == []
    emu.set_party([dict(nuzlocke_dead=True, hp=12)])
    assert ("rule", "nuzlocke", "A fainted Nuzlocke Pokémon has HP again") in kinds(run_checks(det, emu, 3, game=HACK))
    emu.clear_flags = True


def battle(emu, det, game, during=lambda: None, trainer=False, move=True):
    """Run a battle: start, something during, end."""
    out = []
    emu.set_in_battle(True)
    emu.w32(ram.DEFAULT_ADDRESSES["gBattleTypeFlags"], 8 if trainer else 0)
    out += det.check(state(emu, game), ("UP",), 1, last_was_move=move)
    during()
    out += det.check(state(emu, game), ("A",), 2)
    emu.set_in_battle(False)
    out += det.check(state(emu, game), ("A",), 3)
    return out


def test_no_items_in_battle():
    emu = FakeEmulator()
    emu.set_flag(HACK.flags["HACK_NO_BATTLE_ITEMS"])
    emu.set_party([dict(level=10)])
    off = HACK.layout["sb1_bag_pockets"]["items"][0]
    enc = struct.unpack("<I", emu.read(0x02024588 + HACK.layout["sb2_encryption_key"], 4))[0] & 0xFFFF
    emu.write(SB1 + off, struct.pack("<HH", 13, 3 ^ enc))  # 3 Potions
    det = Detectors(HACK)
    det.check(state(emu, HACK), ("A",), 0)
    assert battle(emu, det, HACK) == []
    found = battle(emu, det, HACK, during=lambda: emu.write(SB1 + off, struct.pack("<HH", 13, 2 ^ enc)))
    assert kinds(found) == [("rule", "no_items", "A bag item was used in battle with NO ITEMS IN BATTLE on")]


def test_nuzlocke_second_catch_in_an_area():
    emu = FakeEmulator()
    emu.set_flag(HACK.flags["HACK_NUZLOCKE"])
    emu.set_flag(ram.FLAG_SYS_POKEDEX_GET)
    emu.set_map(3, 19)  # Route 1
    emu.set_party([dict(level=10)])
    area = HACK.maps[(3, 19)]["section_index"] - HACK.p["kanto_mapsec_start"]
    off = HACK.layout["sb1_nuzlocke_areas"][0]
    det = Detectors(HACK)
    det.check(state(emu, HACK), ("A",), 0)

    def use_area():
        emu.write(SB1 + off + area // 8, bytes([1 << (area % 8)]))

    def catch():
        emu.set_party([dict(level=10), dict(level=3, species=16)])

    # The first encounter uses the area (the game sets its bit): no problem,
    # and it confirms where the bits are.
    assert battle(emu, det, HACK, during=lambda: (use_area(), catch())) == []
    assert det.areas_confirmed
    # A second catch there breaks the rule.
    found = battle(emu, det, HACK, during=lambda: emu.set_party([dict(level=10), dict(level=3, species=16),
                                                                 dict(level=4)]))
    assert kinds(found) == [("rule", "nuzlocke", "Caught a second Pokémon in a used Nuzlocke area")]
    # Trainer battles and scripted (non-walking) encounters don't count.
    more = [dict(level=10), dict(level=3, species=16), dict(level=4)]
    assert battle(emu, det, HACK, trainer=True, during=lambda: emu.set_party(more + [dict(level=5)])) == []
    assert battle(emu, det, HACK, move=False, during=lambda: emu.set_party(more + [dict(level=5)] * 2)) == []


# --- explorer ----------------------------------------------------------------------------

def world():
    """A 7x5 room (map 4,1) with a pillar, and a door at (3,0) to a 3x3 room (map 4,0) and back."""
    emu = FakeEmulator()
    emu.set_map(4, 1)
    emu.set_pos(1, 1)
    emu.walls = {(4, 1, 3, 2), (4, 1, 3, 3)}
    emu.bounds = (7, 5)
    emu.warps = {(4, 1, 3, -1): (4, 0, 1, 2), (4, 0, 1, 3): (4, 1, 3, 0)}
    return emu


def test_explorer_covers_a_room_and_finds_the_door():
    emu = world()
    ex = Explorer(random.Random(1), interact_prob=0, menu_prob=0)
    for _ in range(800):
        a = ex.next(state(emu))
        emu.press(a.buttons, a.hold)
    room = ex.maps[(4, 1)]
    assert ex.maps[(4, 0)].visited >= {(1, 2)}
    assert room.visited == {(x, y) for x in range(7) for y in range(5)} - {(3, 2), (3, 3)}
    assert (3, 0, "UP") in room.exits and room.exits[(3, 0, "UP")] == (4, 0)
    assert (4, 0) in ex.maps
    assert (1, 1, "UP") not in room.exits and (1, 0, "UP") in room.blocked


def test_explorer_presses_a_at_obstacles_and_b_for_text():
    emu = world()
    ex = Explorer(random.Random(2), interact_prob=0, menu_prob=0)
    pressed = []
    for _ in range(120):
        a = ex.next(state(emu))
        pressed.append(a.tag)
        emu.press(a.buttons, a.hold)
    assert "interact" in pressed and "text" in pressed


# --- a whole session ------------------------------------------------------------------------

class BuggyEmulator(FakeEmulator):
    """Corrupts the party once the game has run a while: a reproducible bug."""

    def press(self, buttons, frames):
        super().press(buttons, frames)
        if self.frame > 4000 and not self.done:
            self.done = True
            raw = bytearray(self.read(self.party_slot(0), 100))
            raw[0x30] ^= 0xFF  # flip a byte of encrypted data
            self.write(self.party_slot(0), bytes(raw))

    done = False

    def save_state(self):
        import pickle
        return pickle.dumps((self.mem, self.frame, self.done))

    def load_state(self, s):
        import pickle
        self.mem, self.frame, self.done = pickle.loads(s)


def test_session_captures_and_reproduces_a_bug(tmp_path):
    emu = BuggyEmulator()
    emu.bounds = (12, 12)
    emu.set_party([dict(level=10)])
    start = Start("state", "test", emu.save_state())
    t = Tester(emu, VANILLA, tmp_path, worker=0, seed=3, log=None)
    found = t.session(start, 400)
    assert ("corrupt", "party", "Bad Egg / corrupt Pokémon data") in kinds(found)
    folders = list((tmp_path / "findings").iterdir())
    assert len(folders) == 1
    d = folders[0]
    for f in ["before.state", "inputs.json", "screenshot.png", "clip.gif", "finding.json"]:
        assert (d / f).exists(), f
    info = json.loads((d / "finding.json").read_text())
    assert info["extra"]["reproduced"] is True
    assert info["extra"]["start"] == "test"
    assert t.stats.steps == 400 and t.stats.maps


def test_hang_ends_the_session(tmp_path):
    emu = FakeEmulator()
    emu.bounds = (8, 8)
    start = Start("state", "s", emu.save_state())
    emu.crashed = True
    t = Tester(emu, VANILLA, tmp_path, seed=1, log=None)
    emu.load_state = lambda s: None  # keep it crashed
    found = t.session(start, 1000)
    assert found[-1].check == "hang" and t.stats.steps < 1000


def test_pool_and_pick_start(tmp_path):
    out = tmp_path
    rng = random.Random(0)
    starts = [Start("state", "mine", b"x")]
    assert pick_start(rng, starts, out, VANILLA).label == "mine"  # empty pool
    for g, n in [(3, 0), (3, 19)]:
        d = out / "pool" / f"{g}_{n}"
        d.mkdir(parents=True)
        (d / "a.state").write_bytes(b"state")
    (out / "stats-w0.json").write_text(json.dumps({"maps": {"PalletTown": 10000}}))
    labels = [pick_start(rng, starts, out, VANILLA).label for _ in range(300)]
    assert labels.count("pool:Route1") > 5 * labels.count("pool:PalletTown")  # favours little-visited maps
    assert labels.count("mine") > 50


def test_report(tmp_path):
    emu = BuggyEmulator()
    emu.bounds = (12, 12)
    emu.set_party([dict(level=10)])
    t = Tester(emu, VANILLA, tmp_path, seed=3, log=None)
    t.session(Start("state", "test", emu.save_state()), 300)
    (tmp_path / "stats-w0.json").write_text(json.dumps(t.stats.to_json()))
    (tmp_path / "config.json").write_text(json.dumps({"game": "firered", "rom_note": "test ROM", "started": 0}))
    page = write_report(tmp_path).read_text()
    assert "Bad Egg / corrupt Pokémon data" in page and "maps visited" in page
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["findings"][0]["reproduced"] is True and summary["presses"] == 300
