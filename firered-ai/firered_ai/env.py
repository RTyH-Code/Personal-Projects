"""Gymnasium environment for Pokémon FireRed."""

from __future__ import annotations

import gzip
import os
import random
from pathlib import Path

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .goals import Goals
from .maps import map_name
from .progress import MIN_GAIN, ProgressPool, progress_score
from .ram import DEFAULT_ADDRESSES, GameState, read_state
from .rewards import RewardTracker

ACTIONS = [("A",), ("B",), ("UP",), ("DOWN",), ("LEFT",), ("RIGHT",), ("START",)]
ACTION_NAMES = ["A", "B", "UP", "DOWN", "LEFT", "RIGHT", "START"]

SCREEN_SHAPE = (80, 120)  # GBA screen (160x240) at half size
FRAME_STACK = 3
EXPLORE_SIZE = 48  # tiles shown around the player in the exploration map
N_RECENT_ACTIONS = 3


def load_state_file(path: str | os.PathLike) -> bytes:
    data = Path(path).read_bytes()
    return gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data


def save_state_file(path: str | os.PathLike, state: bytes) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(gzip.compress(state))


class FireRedEnv(gym.Env):
    """The agent sees the screen, a map of where it has been, and a few stats.

    Each step presses one button, then waits for the game to react. The
    episode ends ("terminated") when every goal is met, or is cut off
    ("truncated") after max_steps presses.
    """

    metadata = {"render_modes": ["rgb_array"], "render_fps": 60}

    def __init__(
        self,
        rom_path: str | None = None,
        start_state: str | None = None,
        max_steps: int = 8192,
        press_frames: int = 8,
        wait_frames: int = 16,
        allow_start: bool = False,
        reward_weights: dict[str, float] | None = None,
        addresses: dict[str, int] | None = None,
        milestone_dir: str | None = None,
        goals: Goals | None = None,
        progress_dir: str | None = None,
        progress_prob: float = 0.8,
        render_mode: str | None = None,
        emulator=None,
    ):
        super().__init__()
        if emulator is None:
            from .emulator import Emulator

            if rom_path is None:
                raise ValueError("rom_path is required")
            emulator = Emulator(rom_path)
        self.emu = emulator
        self.start_state = load_state_file(start_state) if start_state else self.emu.save_state()
        self.max_steps = max_steps
        self.press_frames = press_frames
        self.wait_frames = wait_frames
        self.actions = ACTIONS if allow_start else ACTIONS[:-1]
        self.addresses = addresses or DEFAULT_ADDRESSES
        self.goals = goals if goals is not None else Goals()
        self.rewards = RewardTracker(reward_weights or {}, self.goals)
        self.milestone_dir = Path(milestone_dir) if milestone_dir else None
        self.pool = ProgressPool(progress_dir) if progress_dir else None
        self.progress_prob = progress_prob
        self.rng = random.Random()
        self.render_mode = render_mode

        self.action_space = spaces.Discrete(len(self.actions))
        self.observation_space = spaces.Dict(
            {
                "screen": spaces.Box(0, 255, (*SCREEN_SHAPE, FRAME_STACK), np.uint8),
                "explored": spaces.Box(0, 255, (EXPLORE_SIZE, EXPLORE_SIZE, 1), np.uint8),
                "stats": spaces.Box(0.0, 1.0, (self._stats_size(),), np.float32),
            }
        )

    # --- gym API -----------------------------------------------------------

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self.rng.seed(seed)
        picked = None
        if self.pool is not None and self.rng.random() < self.progress_prob:
            picked = self.pool.sample(self.rng)
        if picked is not None:
            state, tiles, _ = picked
            self.emu.load_state(state)
        else:
            tiles = None
            self.emu.load_state(self.start_state)
        self.steps = 0
        self.frames = np.zeros((*SCREEN_SHAPE, FRAME_STACK), np.uint8)
        self.recent_actions = [len(self.actions)] * N_RECENT_ACTIONS  # "none"
        self.state = self._read()
        self.rewards.reset(self.state, tiles)
        self.from_pool = picked is not None
        self.best_badges = self.state.badge_count if self.state.valid else 0
        self.start_score = self.best_score = self._score()
        self._push_frame()
        return self._obs(), self._info()

    def step(self, action):
        buttons = self.actions[int(action)]
        self.emu.press(buttons, self.press_frames)
        self.emu.press((), self.wait_frames)
        self.steps += 1
        self.recent_actions = [int(action)] + self.recent_actions[:-1]

        self.state = self._read()
        reward = self.rewards.step(self.state)
        self._push_frame()
        self._save_milestones()
        self._save_progress()
        terminated = self.rewards.complete
        truncated = self.steps >= self.max_steps and not terminated
        return self._obs(), reward, terminated, truncated, self._info()

    def render(self):
        return self.emu.screen()

    def close(self):
        self.emu.close()

    # --- helpers -----------------------------------------------------------

    def _read(self) -> GameState:
        return read_state(self.emu.read, self.addresses)

    def _push_frame(self) -> None:
        gray = self.emu.screen()[::2, ::2].astype(np.uint16).sum(axis=2) // 3
        self.frames = np.roll(self.frames, 1, axis=2)
        self.frames[:, :, 0] = gray.astype(np.uint8)

    def _explored(self) -> np.ndarray:
        m = np.zeros((EXPLORE_SIZE, EXPLORE_SIZE, 1), np.uint8)
        s = self.state
        if not s.valid:
            return m
        half = EXPLORE_SIZE // 2
        for x, y in self.rewards.tiles.get(s.map_id, ()):
            i, j = y - s.y + half, x - s.x + half
            if 0 <= i < EXPLORE_SIZE and 0 <= j < EXPLORE_SIZE:
                m[i, j, 0] = 255
        m[half, half, 0] = 128  # the player
        return m

    def _stats_size(self) -> int:
        return 6 + 6 + 8 + 7 + (len(self.actions) + 1) * N_RECENT_ACTIONS

    def _stats(self) -> np.ndarray:
        s = self.state
        hp = np.zeros(6, np.float32)
        lv = np.zeros(6, np.float32)
        for i, mon in enumerate(s.party[:6]):
            hp[i] = mon.hp / mon.max_hp
            lv[i] = mon.level / 100
        badges = np.array([(s.badges >> i) & 1 for i in range(8)], np.float32)
        goal = self.goals.status(s) if s.valid else {}
        misc = np.array(
            [
                float(s.in_battle),
                s.dex_owned / 386,
                min(s.money / 100_000, 1.0),
                self.steps / self.max_steps,
                float(s.champion),
                float(s.national_dex),
                goal.get("pokedex", 0.0),
            ],
            np.float32,
        )
        recent = np.zeros((N_RECENT_ACTIONS, len(self.actions) + 1), np.float32)
        recent[np.arange(N_RECENT_ACTIONS), self.recent_actions] = 1
        return np.concatenate([hp, lv, badges, misc, recent.ravel()])

    def _obs(self):
        return {"screen": self.frames.copy(), "explored": self._explored(), "stats": self._stats()}

    def _info(self):
        s = self.state
        info = {
            "steps": self.steps,
            "valid": s.valid,
            "map": map_name(*s.map_id),
            "x": s.x,
            "y": s.y,
            "badges": s.badge_count,
            "level_sum": s.level_sum,
            "party_size": len(s.party),
            "dex_owned": s.dex_owned,
            "tiles_explored": self.rewards.tile_count,
            "maps_explored": len(self.rewards.tiles),
            "champion": s.champion,
            "goal_progress": self.goals.fraction(s) if s.valid else 0.0,
            "complete": self.rewards.complete,
            "from_pool": self.from_pool,
            "start_score": self.start_score,
            "score": self.best_score,
        }
        if s.valid:
            info.update({f"goal/{k}": v for k, v in self.goals.status(s).items()})
        info.update({f"reward/{k}": v for k, v in self.rewards.totals.items()})
        return info

    def _score(self) -> float:
        s = self.state
        if not s.valid:
            return -1
        return progress_score(s, self.goals, len(self.rewards.tiles), self.rewards.tile_count)

    def _save_progress(self) -> None:
        """Add this state to the pool when it's further than this episode has been."""
        s = self.state
        if self.pool is None or not s.valid or s.in_battle or s.all_fainted:
            return
        score = self._score()
        if score < self.best_score + MIN_GAIN:
            return
        self.best_score = score
        if self.pool.worth_saving(score):
            info = {"map": map_name(*s.map_id), "badges": s.badge_count, "level_sum": s.level_sum,
                    "dex_owned": s.dex_owned, "champion": s.champion}
            self.pool.add(score, self.emu.save_state(), self.rewards.tile_list(), info)

    def _save_milestones(self) -> None:
        """Keep a save state each time an agent gets a new badge, so you can look."""
        if self.milestone_dir is None or not self.state.valid:
            return
        if self.state.badge_count > self.best_badges:
            self.best_badges = self.state.badge_count
            name = f"badge{self.best_badges}_{map_name(*self.state.map_id)}_{os.getpid()}.state"
            save_state_file(self.milestone_dir / name, self.emu.save_state())
