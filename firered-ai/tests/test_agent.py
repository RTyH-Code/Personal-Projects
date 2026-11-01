import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fake_emulator import FakeEmulator  # noqa: E402

from firered_ai import ram  # noqa: E402
from firered_ai.bootstrap import BEDROOM, skip_intro  # noqa: E402
from firered_ai.env import FireRedEnv  # noqa: E402
from firered_ai.maps import map_name  # noqa: E402
from firered_ai.rewards import DEFAULT_WEIGHTS, RewardTracker  # noqa: E402


def test_read_state():
    emu = FakeEmulator()
    emu.set_party([(5, 20, 20), (12, 0, 33)])
    emu.set_flag(ram.FLAG_BADGE01)
    emu.set_flag(ram.FLAG_BADGE01 + 2)
    emu.set_flag(ram.FLAG_SYS_POKEMON_GET)
    emu.set_owned(11)
    emu.set_money(3000)
    emu.set_in_battle(True)
    s = ram.read_state(emu.read)
    assert s.valid
    assert map_name(*s.map_id) == "PalletTown_PlayersHouse_2F"
    assert (s.x, s.y) == (5, 5)
    assert [m.level for m in s.party] == [5, 12]
    assert s.level_sum == 17
    assert s.badges == 0b101 and s.badge_count == 2
    assert s.has_pokemon and not s.has_pokedex
    assert s.dex_owned == 11
    assert s.money == 3000
    assert s.in_battle
    assert s.hp_fraction == pytest.approx(20 / 53)
    assert not s.all_fainted


def test_invalid_before_new_game():
    assert not ram.read_state(FakeEmulator(valid=False).read).valid


def test_rewards():
    emu = FakeEmulator()
    w = DEFAULT_WEIGHTS
    t = RewardTracker()
    t.reset(ram.read_state(emu.read))

    assert t.step(ram.read_state(emu.read)) == 0  # start tile is free
    emu.set_pos(5, 6)
    assert t.step(ram.read_state(emu.read)) == pytest.approx(w["explore"])
    emu.set_pos(5, 5)
    assert t.step(ram.read_state(emu.read)) == 0  # been here
    emu.set_map(3, 0)
    assert t.step(ram.read_state(emu.read)) == pytest.approx(w["explore"] + w["new_map"])

    emu.set_party([(5, 20, 20)])
    emu.set_flag(ram.FLAG_SYS_POKEMON_GET)
    assert t.step(ram.read_state(emu.read)) == pytest.approx(w["starter"])  # no level reward
    emu.set_party([(7, 24, 24)])
    assert t.step(ram.read_state(emu.read)) == pytest.approx(2 * w["level"])

    emu.set_party([(7, 0, 24)])
    assert t.step(ram.read_state(emu.read)) == pytest.approx(w["blackout"])
    emu.set_party([(7, 24, 24)])
    assert t.step(ram.read_state(emu.read)) == 0  # heal after blackout doesn't count
    emu.set_party([(7, 12, 24)])
    t.step(ram.read_state(emu.read))
    emu.set_party([(7, 24, 24)])
    assert t.step(ram.read_state(emu.read)) == pytest.approx(0.5 * w["heal"])

    emu.set_flag(ram.FLAG_BADGE01)
    emu.set_owned(2)
    assert t.step(ram.read_state(emu.read)) == pytest.approx(w["badge"] + 2 * w["dex"])
    emu.set_flag(ram.FLAG_BADGE01, False)  # can't farm it
    t.step(ram.read_state(emu.read))
    emu.set_flag(ram.FLAG_BADGE01)
    assert t.step(ram.read_state(emu.read)) == 0


def test_env_obs_and_steps():
    env = FireRedEnv(emulator=FakeEmulator(), max_steps=20)
    from gymnasium.utils.env_checker import check_env

    check_env(env, skip_render_check=True)
    obs, info = env.reset()
    assert env.observation_space.contains(obs)
    assert env.action_space.n == 6  # no START by default
    total, steps = 0.0, 0
    for _ in range(20):
        obs, r, term, trunc, info = env.step(3)  # DOWN
        total += r
        steps += 1
        assert env.observation_space.contains(obs)
        if trunc:
            break
    assert steps == 20 and trunc
    assert info["tiles_explored"] == 21
    assert total == pytest.approx(20 * DEFAULT_WEIGHTS["explore"])
    # The exploration map marks the trail above the player.
    half = obs["explored"].shape[0] // 2
    assert obs["explored"][half - 1, half, 0] == 255 and obs["explored"][half, half, 0] == 128
    # Reset restores the start state.
    env.reset()
    assert (env.state.x, env.state.y) == (5, 5)


def test_env_allow_start():
    assert FireRedEnv(emulator=FakeEmulator(), allow_start=True).action_space.n == 7


class IntroEmulator(FakeEmulator):
    """Starts on the 'title screen' and reaches the bedroom after 50 presses."""

    def __init__(self):
        super().__init__(valid=False)

    def press(self, buttons, frames):
        super().press(buttons, frames)
        if len(self.presses) == 50:
            self.w32(ram.DEFAULT_ADDRESSES["gSaveBlock1Ptr"], 0x0202552C)
            self.w32(ram.DEFAULT_ADDRESSES["gSaveBlock2Ptr"], 0x02024588)
            self.set_map(*BEDROOM)


def test_skip_intro():
    emu = IntroEmulator()
    assert skip_intro(emu, log=None)
    assert ("START",) in emu.presses and ("A",) in emu.presses


def test_skip_intro_gives_up():
    assert not skip_intro(FakeEmulator(valid=False), max_presses=30, log=None)


def test_symbols_from_map(tmp_path, capsys, monkeypatch):
    m = tmp_path / "pokefirered.map"
    m.write_text(" .bss  0x03005008  0x8 src/load_save.o\n"
                 "                0x03005008                gSaveBlock1Ptr\n"
                 "                0x02024284                gPlayerParty\n")
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
    import symbols_from_map

    monkeypatch.setattr(sys, "argv", ["x", str(m)])
    symbols_from_map.main()
    out = capsys.readouterr().out
    p = tmp_path / "a.json"
    p.write_text(out)
    addrs = ram.load_addresses(str(p))
    assert addrs["gSaveBlock1Ptr"] == 0x03005008 and addrs["gPlayerParty"] == 0x02024284
    assert addrs["gMain"] == ram.DEFAULT_ADDRESSES["gMain"]
