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
# Moves the playtester never picks to attack with: they faint the user, or only
# work when the target is asleep.
AVOID_EFFECTS = {"EFFECT_EXPLOSION", "EFFECT_DREAM_EATER", "EFFECT_MEMENTO", "EFFECT_FOCUS_PUNCH",
                 "EFFECT_SNORE", "EFFECT_FAKE_OUT"}


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
    def trainer_ids(self) -> dict[str, int]:
        """TRAINER_ constant without the prefix -> trainer number."""
        return {v["id"]: k for k, v in self.trainers.items() if v.get("id")}

    @cached_property
    def fightable_trainers(self) -> dict[int, dict]:
        """Trainers some map's script battles."""
        return {k: v for k, v in self.trainers.items() if v["maps"]}

    def trainer_name(self, trainer: int) -> str:
        t = self.trainers.get(trainer)
        return f"{t['class'].replace('_', ' ').title()} {t['name'].title()}".strip() if t else f"trainer {trainer}"

    def flag(self, name: str) -> int | None:
        return self.flags.get(name)

    # --- battles -------------------------------------------------------------

    @cached_property
    def moves(self) -> dict[int, dict]:
        return {int(k): v for k, v in self.p.get("moves", {}).items()}

    @cached_property
    def species_types(self) -> dict[int, list[int]]:
        return {int(k): v for k, v in self.p.get("species_types", {}).items()}

    @cached_property
    def type_chart(self) -> dict[tuple[int, int], float]:
        return {(a, d): m / 10 for a, d, m in self.p.get("type_chart", [])}

    def effectiveness(self, move_type: int, defender_species: int) -> float:
        mult = 1.0
        for t in dict.fromkeys(self.species_types.get(defender_species, [])):  # once per distinct type
            mult *= self.type_chart.get((move_type, t), 1.0)
        return mult

    def move_score(self, mon, slot: int, target) -> float:
        """Roughly how much damage a move does: power x same-type bonus x matchup x accuracy."""
        move = self.moves.get(mon.moves[slot]) if slot < len(mon.moves) else None
        if move is None or not mon.moves[slot] or (slot < len(mon.pp) and mon.pp[slot] == 0):
            return -1.0
        power = move["power"]
        if power == 0 or move["effect"] in AVOID_EFFECTS:
            return 0.0  # status moves, and ones that hurt us
        if power == 1:  # fixed or level-based damage (Seismic Toss, Night Shade, ...)
            power = max(40, getattr(mon, "level", 40))
        score = power * (move["accuracy"] or 100) / 100
        if move["type"] in self.species_types.get(mon.species, []):
            score *= 1.5
        if target is not None:
            score *= self.effectiveness(move["type"], target.species)
        return score

    def best_move(self, mon, target) -> int:
        """The move slot (0-3) to use against `target`: the most damage, or slot 0 if nothing helps."""
        scores = [self.move_score(mon, i, target) for i in range(4)]
        best = max(range(4), key=lambda i: scores[i])
        return best if scores[best] > 0 else max(range(4), key=lambda i: (scores[i] >= 0, -i))

    def has_damaging_pp(self, mon) -> bool:
        return any(self.move_score(mon, i, None) > 0 for i in range(4))

    def next_gym_level(self, state) -> int:
        """The highest level on the next Gym Leader's team (the League's after 8 badges)."""
        levels = self.p.get("gym_levels") or {}
        leaders = levels.get("leaders", [])
        for i, lvl in enumerate(leaders):
            if not state.flag(self.flags["BADGE01_GET"] + i):
                return lvl
        return levels.get("league", 100)

    def item(self, name: str) -> int | None:
        return self.p.get("items", {}).get(name)

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
