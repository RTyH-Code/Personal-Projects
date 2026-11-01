import os
import random
import struct
import sys
import zlib
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fake_emulator import SB2, FakeEmulator  # noqa: E402

from firered_ai import ram  # noqa: E402
from firered_ai.env import FireRedEnv  # noqa: E402
from firered_ai.goals import KNOWN_ROMS, Goals, PokedexTarget, detect_game  # noqa: E402
from firered_ai.progress import ProgressPool  # noqa: E402
from firered_ai.rewards import DEFAULT_WEIGHTS, RewardTracker  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def own(emu, numbers):
    data = bytearray(ram.DEX_FLAG_BYTES)
    for n in numbers:
        data[(n - 1) // 8] |= 1 << ((n - 1) % 8)
    emu.write(SB2 + ram.SB2_DEX_OWNED, bytes(data))


def test_reads_champion_and_owned_species():
    emu = FakeEmulator()
    own(emu, [1, 25, 151, 386])
    s = ram.read_state(emu.read)
    assert s.owned == {1, 25, 151, 386} and s.dex_owned == 4
    assert not s.champion and not s.national_dex
    emu.set_flag(ram.FLAG_SYS_GAME_CLEAR)
    emu.set_flag(ram.FLAG_SYS_NATIONAL_DEX)
    s = ram.read_state(emu.read)
    assert s.champion and s.national_dex and s.badges == 0


def test_vanilla_pokedex_list():
    dex = PokedexTarget.load("firered")
    names = {v: k for k, v in dex.names.items()}
    assert len(dex.names) == 386
    assert dex.progress(frozenset())[1] == 170
    for leafgreen_only in ["SANDSHREW", "VULPIX", "BELLSPROUT", "SLOWPOKE", "STARYU", "MAGMAR", "PINSIR"]:
        assert names[leafgreen_only] not in dex.species
    for trade_evo in ["ALAKAZAM", "MACHAMP", "GOLEM", "GENGAR"]:
        assert names[trade_evo] not in dex.species
    assert names["MEW"] not in dex.species and names["DEOXYS"] not in dex.species
    assert names["EKANS"] in dex.required and names["MEWTWO"] in dex.required
    # Starter choice comes with its roaming legendary.
    starters = next(alts for alts in dex.choices if names["BULBASAUR"] in set().union(*alts))
    assert {names["BULBASAUR"], names["VENUSAUR"], names["ENTEI"]} <= next(a for a in starters if names["BULBASAUR"] in a)
    assert not dex.required & dex.species - dex.required


def test_qol_hard_pokedex_list():
    dex = PokedexTarget.load("firered-qol-hard")
    names = {v: k for k, v in dex.names.items()}
    # The hack makes every species obtainable in one save, with no either/or choices.
    assert dex.progress(frozenset())[1] == 386 and not dex.choices
    for fixed in ["ESPEON", "UMBREON", "MILOTIC", "OMASTAR", "KABUTOPS", "LILEEP", "ANORITH", "DEOXYS"]:
        assert names[fixed] in dex.required


def test_pokedex_choices():
    dex = PokedexTarget("t", frozenset({1, 2}), [[frozenset({10, 11}), frozenset({20})]])
    assert dex.progress(frozenset()) == (0, 3)  # smallest option when nothing is owned
    assert dex.progress(frozenset({1, 10})) == (2, 4)
    assert not dex.complete(frozenset({1, 2, 10}))
    assert dex.complete(frozenset({1, 2, 10, 11}))
    assert dex.complete(frozenset({1, 2, 20}))
    assert dex.missing(frozenset({1, 10})) == [2, 11]


def test_goals_parse():
    dex = PokedexTarget.load("firered")
    g = Goals.parse("badges,pokedex", dex)
    assert g.badges and not g.champion and g.pokedex is dex
    assert not Goals.parse("none", None).any
    with pytest.raises(ValueError):
        Goals.parse("badges,pokdex", dex)
    with pytest.raises(ValueError):
        Goals.parse("pokedex", None)


def test_detect_game(tmp_path):
    rom = tmp_path / "x.gba"
    rom.write_bytes(b"not a real rom")
    assert detect_game(str(rom)) is None
    bps = REPO / "firered-qol-hard" / "FireRed-QoL-Hard.bps"
    if bps.exists():
        source, target = struct.unpack("<II", bps.read_bytes()[-12:-4])
        assert KNOWN_ROMS[source] == "firered" and KNOWN_ROMS[target] == "firered_qol_hard"
    assert zlib.crc32(b"not a real rom") not in KNOWN_ROMS


def test_goal_rewards_and_episode_end():
    emu = FakeEmulator()
    emu.set_party([(5, 20, 20)])
    dex = PokedexTarget("t", frozenset({1, 4}))
    env = FireRedEnv(emulator=emu, goals=Goals(badges=True, champion=True, pokedex=dex), max_steps=50)
    env.reset()
    w = DEFAULT_WEIGHTS

    own(emu, [1, 99])  # 99 isn't on the list, so only one counts
    _, r, term, _, info = env.step(0)
    assert r == pytest.approx(w["dex"]) and not term
    assert info["goal/pokedex"] == 0.5

    for i in range(8):
        emu.set_flag(ram.FLAG_BADGE01 + i)
    own(emu, [1, 4, 99])
    _, r, term, _, info = env.step(0)
    assert r == pytest.approx(8 * w["badge"] + w["dex"]) and not term

    emu.set_flag(ram.FLAG_SYS_GAME_CLEAR)
    _, r, term, trunc, info = env.step(0)
    assert r == pytest.approx(w["champion"] + w["complete"])
    assert term and not trunc and info["complete"] and info["goal_progress"] == 1.0


def test_start_state_progress_is_not_rewarded():
    emu = FakeEmulator()
    emu.set_flag(ram.FLAG_SYS_GAME_CLEAR)
    own(emu, [1, 2, 3])
    t = RewardTracker()
    t.reset(ram.read_state(emu.read))
    assert t.step(ram.read_state(emu.read)) == 0


def test_progress_pool(tmp_path):
    pool = ProgressPool(tmp_path, keep=3, sample_top=2)
    assert pool.sample(random.Random(0)) is None
    for score in [5, 1, 9, 7]:
        pool.add(score, f"state{score}".encode(), [(3, 0, score, 0)], {"map": "M"})
    assert len(list(tmp_path.glob("*.state"))) == 3 and len(list(tmp_path.glob("*.json.gz"))) == 3
    assert pool.best_score() == 9
    assert not pool.worth_saving(4) and pool.worth_saving(6)
    seen = {pool.sample(random.Random(i))[0] for i in range(20)}
    assert seen == {b"state9", b"state7"}  # only the top two
    state, tiles, score = pool.sample(random.Random(0))
    assert tiles == [(3, 0, int(score), 0)]


def test_env_continues_from_progress_pool(tmp_path):
    env = FireRedEnv(emulator=FakeEmulator(), progress_dir=str(tmp_path), progress_prob=1.0, max_steps=60)
    env.reset(seed=0)
    for _ in range(49):
        env.step(3)  # DOWN, onto new tiles
    assert not list(tmp_path.glob("*.state"))  # not enough progress yet
    for _ in range(11):
        env.step(3)
    assert len(list(tmp_path.glob("*.state"))) == 1
    _, info = env.reset(seed=1)
    assert info["from_pool"]
    assert (env.state.x, env.state.y) == (5, 55)  # where the run had got to when it was saved
    assert info["tiles_explored"] == 51  # carried over
    _, r, *_ = env.step(2)  # UP, back over old ground: no explore reward
    assert r == 0


def test_finished_states_stay_out_of_the_pool(tmp_path):
    emu = FakeEmulator()
    env = FireRedEnv(emulator=emu, goals=Goals(badges=True, champion=False), progress_dir=str(tmp_path))
    env.reset()
    for i in range(8):
        emu.set_flag(ram.FLAG_BADGE01 + i)  # +80,000 score, and every goal met
    _, _, term, _, _ = env.step(0)
    assert term
    assert not list(tmp_path.glob("*.state"))
