"""A thin wrapper around the mGBA core that ships with stable-retro.

stable-retro only loads ROMs it has an "integration" for, so we create one
on the fly in a cache directory. The ROM never leaves your machine.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import warnings
from pathlib import Path

import numpy as np

GAME_NAME = "PokemonFireRedAI-GbAdvance"
# stable-retro's GBA button order.
BUTTONS = ["B", None, "SELECT", "START", "UP", "DOWN", "LEFT", "RIGHT", "A", None, "L", "R"]
FLASH_BASE, FLASH_SIZE = 0x0E000000, 0x20000
DEFAULT_CACHE = Path(os.environ.get("FIRERED_AI_CACHE", Path.home() / ".cache" / "firered-ai"))


def _import_retro():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            import stable_retro as retro
        except ImportError:
            import retro
    return retro


def prepare_integration(rom_path: str | os.PathLike, cache_dir: Path = DEFAULT_CACHE) -> Path:
    """Write a stable-retro integration for this ROM and return its parent dir."""
    rom = Path(rom_path).read_bytes()
    sha = hashlib.sha1(rom).hexdigest()
    root = Path(cache_dir) / sha
    game = root / GAME_NAME
    if not (game / "rom.sha").exists():
        game.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(rom_path, game / "rom.gba")
        (game / "data.json").write_text(json.dumps({"info": {}}))
        (game / "scenario.json").write_text(
            json.dumps({"done": {"variables": {}}, "reward": {"variables": {}}})
        )
        (game / "metadata.json").write_text("{}")
        (game / "rom.sha").write_text(sha)  # written last: marks the dir complete
    return root


class Emulator:
    """One GBA emulator. stable-retro allows one per process."""

    def __init__(self, rom_path: str, cache_dir: Path = DEFAULT_CACHE):
        retro = _import_retro()
        retro.data.Integrations.add_custom_path(str(prepare_integration(rom_path, cache_dir)))
        self.env = retro.make(
            GAME_NAME,
            state=retro.State.NONE,
            inttype=retro.data.Integrations.CUSTOM_ONLY,
            use_restricted_actions=retro.Actions.ALL,
            render_mode=None,
        )
        self.env.reset()
        self._screen = None
        self._blocks = None
        self.power_on = self.save_state()  # for booting again with a battery save

    def press(self, buttons: tuple[str, ...], frames: int) -> None:
        """Hold `buttons` for `frames` frames (60 frames = 1 second)."""
        mask = np.array([1 if b in buttons else 0 for b in BUTTONS], dtype=np.int8)
        em = self.env.em
        for _ in range(frames):
            em.set_button_mask(mask, 0)
            em.step()
        self._invalidate()

    def _invalidate(self) -> None:
        self.env.data.update_ram()
        self._screen = None
        self._blocks = None

    def screen(self) -> np.ndarray:
        """Current frame, (160, 240, 3) uint8."""
        if self._screen is None:
            self._screen = self.env.em.get_screen()
        return self._screen

    def read(self, address: int, size: int) -> bytes:
        if self._blocks is None:  # one snapshot of RAM per emulator step
            self._blocks = list(self.env.data.memory.blocks.items())
        for base, block in self._blocks:
            if base <= address and address + size <= base + len(block):
                return block[address - base : address - base + size]
        raise ValueError(f"address {address:#x} is not mapped")

    def save_state(self) -> bytes:
        return self.env.em.get_state()

    def load_state(self, state: bytes) -> None:
        self.env.em.set_state(state)
        self._invalidate()

    def boot_with_save(self, sav: bytes) -> None:
        """Power on again with `sav` (a .sav file from mGBA or another emulator) on the cartridge.

        FireRed saves to a 128 KiB flash chip. stable-retro exposes it at
        0x0E000000; the game reads it when it boots. Save states don't include
        it, so it stays until the next call.
        """
        self.load_state(self.power_on)
        memory = self.env.data.memory
        data = sav[:FLASH_SIZE].ljust(FLASH_SIZE, b"\xff")
        for i, b in enumerate(data):
            memory.assign(FLASH_BASE + i, "|u1", b)
        self._invalidate()

    def close(self) -> None:
        self.env.close()
