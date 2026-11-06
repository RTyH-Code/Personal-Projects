"""Which game a ROM is, and what the playtester knows about it.

Profiles in firered_ai/data/games/ are generated from the game's source by
tools/game_data.py. A ROM is matched to one:

- FireRed QoL + Hard: by the "QoL+HARD R<n>" string its Options screen shows,
  so a new release is still recognised. If the release differs from the
  profile's, the playtester warns that the profile may be out of date.
- Vanilla FireRed: by checksum (v1.0 or v1.1), or else by its game code.
"""

from __future__ import annotations

import json
import zlib
from functools import cached_property
from pathlib import Path

GAMES = Path(__file__).parent / "data" / "games"
VANILLA_CRCS = {0xDD88761C: "v1.0", 0x84EE4776: "v1.1"}


class Game:
    def __init__(self, profile: dict):
        self.p = profile
        self.name: str = profile["name"]
        self.release: str | None = (profile.get("release") or {}).get("release")
        self.layout = {**profile["layout"], "dex_count": profile["dex_count"]}
        self.flags: dict[str, int] = profile["flags"]
        self.trainer_flags_start: int = profile["trainer_flags_start"]
        self.level_caps = profile.get("level_caps")
        self.items_count: int = profile["items_count"]
        self.poke_balls = range(profile["poke_balls"][0], profile["poke_balls"][1] + 1)
        self.vars: dict[str, int] = profile["vars"]

    @classmethod
    def load(cls, name: str) -> "Game":
        path = Path(name)
        if not path.exists():
            path = GAMES / f"{name.replace('-', '_')}.json"
        return cls(json.loads(path.read_text()))

    @cached_property
    def maps(self) -> dict[tuple[int, int], dict]:
        return {(m["group"], m["num"]): m for m in self.p["maps"]}

    def map_name(self, group: int, num: int) -> str:
        m = self.maps.get((group, num))
        return m["name"] if m else f"Unknown({group},{num})"

    def map_section(self, group: int, num: int) -> str | None:
        m = self.maps.get((group, num))
        return m["section"] if m else None

    @cached_property
    def species(self) -> dict[int, str]:
        return {int(k): v for k, v in self.p["species"].items()}

    def species_name(self, n: int) -> str:
        return self.species.get(n, f"#{n}")

    @cached_property
    def trainers(self) -> dict[int, dict]:
        return {int(k): v for k, v in self.p["trainers"].items()}

    @cached_property
    def fightable_trainers(self) -> dict[int, dict]:
        """Trainers some map's script battles."""
        return {k: v for k, v in self.trainers.items() if v["maps"]}

    def trainer_name(self, trainer: int) -> str:
        t = self.trainers.get(trainer)
        return f"{t['class'].replace('_', ' ').title()} {t['name'].title()}".strip() if t else f"trainer {trainer}"

    def flag(self, name: str) -> int | None:
        return self.flags.get(name)

    def level_cap(self, state) -> int:
        """The level cap the game applies now (src/pokemon.c Hack_GetLevelCap), or 100."""
        caps = self.level_caps
        f = self.flags
        if not caps or "HACK_LEVEL_CAP" not in f or not state.flag(f["HACK_LEVEL_CAP"]) or state.champion:
            return 100
        unbeaten = [lvl for i, lvl in enumerate(caps["leaders"]) if not state.flag(f["BADGE01_GET"] + i)]
        return min(unbeaten) if unbeaten else caps["league"]


def find_release(rom: bytes, profile: dict) -> str | None:
    """The hack release string in a ROM ("R14"), if the hack's signature is there."""
    info = profile.get("release")
    if not info:
        return None
    sig = bytes(info["signature"])
    i = rom.find(sig)
    if i < 0:
        return None
    chars = info["release_chars"]  # encodings of "R0123456789"
    out = []
    for b in rom[i + len(sig) : i + len(sig) + 6]:
        if b not in chars:
            break
        out.append("R0123456789"[chars.index(b)])
    return "".join(out) or None


def detect(rom_path: str) -> tuple[Game, str]:
    """(profile, description) for a ROM. Raises ValueError if it isn't FireRed."""
    rom = Path(rom_path).read_bytes()
    hack = json.loads((GAMES / "firered_qol_hard.json").read_text())
    release = find_release(rom, hack)
    if release:
        game = Game(hack)
        note = f"FireRed QoL + Hard {release}"
        if release != game.release:
            note += (f" (the playtester's data is from {game.release}; regenerate it with tools/game_data.py "
                     "if this release changed maps, trainers or the save layout)")
        return game, note
    crc = zlib.crc32(rom)
    game = Game.load("firered")
    if crc in VANILLA_CRCS:
        return game, f"Pokémon FireRed (US) {VANILLA_CRCS[crc]}"
    if rom[0xAC:0xB0] == b"BPRE":
        return game, "an unrecognised FireRed (US) ROM; using vanilla FireRed's data"
    raise ValueError(f"{rom_path} isn't Pokémon FireRed (US) (game code {rom[0xAC:0xB0]!r})")
