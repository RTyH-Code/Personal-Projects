"""One playtest worker: plays sessions, watches for bugs, records what it finds.

A session starts from a save state or a battery save and runs for a set
number of button presses. Every press goes through the detectors
(firered_ai/detectors.py). The tester keeps a save state every RING_EVERY
presses, the presses since, and a short video, so each finding comes with:

    findings/<kind>-<check>-<n>/
        finding.json   what happened, where, and whether it reproduced
        before.state   a save state from shortly before (mGBA's own state format)
        inputs.json    the presses from before.state to the problem
        screenshot.png the screen when it was found
        clip.gif       the last ~40 seconds of play
        replay command: python replay.py <rom> findings/<that folder>

Findings that can be re-run from before.state are replayed straight away to
check they really happen.
"""

from __future__ import annotations

import gzip
import json
import random
import time
import traceback
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from .bootstrap import continue_from_save
from .detectors import Detectors, Finding
from .explorer import Action, Explorer
from .game import Game
from .ram import DEFAULT_ADDRESSES, MAIN_HELD_KEYS_RAW, read_state

RING_EVERY = 50  # presses between rolling save states
RING_KEEP = 3
CLIP_EVERY = 2  # record every Nth press
CLIP_FRAMES = 150
MAX_CAPTURES_PER_SIGNATURE = 2
POOL_PER_MAP = 3


@dataclass
class Start:
    kind: str  # state, sav, pool
    label: str
    data: bytes


@dataclass
class Stats:
    """What happened, for coverage and difficulty numbers."""

    steps: int = 0
    sessions: int = 0
    maps: dict = field(default_factory=dict)  # map name -> steps spent there
    trainers_beaten: dict = field(default_factory=dict)  # trainer id -> times
    species_seen: set = field(default_factory=set)
    species_owned: set = field(default_factory=set)
    battles: dict = field(default_factory=dict)  # map name -> {"wild": n, "trainer": n, "blackouts": n, "trainer_losses": n}
    blackouts: list = field(default_factory=list)  # {map, trainer, party levels}
    starts: dict = field(default_factory=dict)  # start label -> sessions

    def to_json(self):
        d = asdict(self)
        d["species_seen"] = sorted(self.species_seen)
        d["species_owned"] = sorted(self.species_owned)
        return d


def screen_hash(screen: np.ndarray) -> int:
    return hash(screen[::4, ::4].tobytes())


class Tester:
    __test__ = False  # not a pytest test class
    def __init__(self, emu, game: Game, out: Path, worker: int = 0, seed: int | None = None,
                 addresses=DEFAULT_ADDRESSES, log=print, stop=None):
        self.emu = emu
        self.game = game
        self.out = Path(out)
        self.worker = worker
        self.rng = random.Random(seed)
        self.addresses = addresses
        self.log = log or (lambda *_: None)
        self.stop = stop  # a multiprocessing.Event, or None
        self.map_visits: dict = {}
        self.explorer = Explorer(self.rng, self.map_visits)
        self.stats = Stats()
        self.captures: dict[str, int] = {}
        self.pool = self.out / "pool"

    # --- plumbing ---------------------------------------------------------------

    def read(self):
        return read_state(self.emu.read, self.addresses, self.game.layout)

    def do(self, a: Action):
        """Press, and return gMain.heldKeysRaw read while the buttons were down."""
        held = None
        if a.buttons:
            self.emu.press(a.buttons, a.hold)
            held = int.from_bytes(self.emu.read(self.addresses["gMain"] + MAIN_HELD_KEYS_RAW, 2), "little")
        elif a.hold:
            self.emu.press((), a.hold)
        if a.wait:
            self.emu.press((), a.wait)
        return held

    def load(self, start: Start) -> bool:
        if start.kind == "sav":
            self.emu.boot_with_save(start.data)
            return continue_from_save(self.emu, self.game, self.addresses, log=None)
        self.emu.load_state(start.data)
        return True

    # --- a session ----------------------------------------------------------------

    def session(self, start: Start, steps: int) -> list[Finding]:
        if not self.load(start):
            self.log(f"[{self.worker}] couldn't load {start.label}")
            return []
        self.stats.sessions += 1
        self.stats.starts[start.label] = self.stats.starts.get(start.label, 0) + 1
        det = Detectors(self.game)
        ring: deque = deque(maxlen=RING_KEEP)  # (step, state, index into actions)
        actions: list = []
        clip: deque = deque(maxlen=CLIP_FRAMES)
        found: list[Finding] = []
        s = self.read()
        prev = s
        self._battle = None
        for step in range(steps):
            if self.stop is not None and self.stop.is_set():
                break
            if step % RING_EVERY == 0:
                ring.append((step, self.emu.save_state(), len(actions)))
                if len(ring) == RING_KEEP:  # drop presses older than the oldest kept state
                    cut = ring[0][2]
                    if cut:
                        actions = actions[cut:]
                        ring = deque(((st, data, i - cut) for st, data, i in ring), maxlen=RING_KEEP)
            a = self.explorer.next(s)
            actions.append(a)
            try:
                held = self.do(a)
            except Exception as e:  # the emulator itself failed
                found.append(Finding("crash", "emulator", "The emulator raised an error", repr(e), step=step,
                                     fatal=True, reproducible=False, extra={"traceback": traceback.format_exc()}))
                break
            s = self.read()
            screen = self.emu.screen()
            if step % CLIP_EVERY == 0:
                clip.append(screen[::2, ::2].copy())
            new = det.check(s, a.buttons, screen_hash(screen), held, step, last_was_move=a.tag == "move")
            self._account(prev, s)
            self._maybe_pool(s)
            prev = s
            for f in new:
                f.extra.setdefault("start", start.label)
                self._capture(f, ring, actions, screen, clip, step)
                found.append(f)
            if any(f.fatal for f in new):
                break
        self.stats.steps += step + 1 if steps else 0
        return found

    # --- coverage, difficulty and the start-point pool ---------------------------------

    def _account(self, p, s) -> None:
        if not s.valid:
            return
        g = self.game
        name = g.map_name(*s.map_id)
        st = self.stats
        st.maps[name] = st.maps.get(name, 0) + 1
        self.map_visits[s.map_id] = self.map_visits.get(s.map_id, 0) + (0 if p.valid and p.map_id == s.map_id else 1)
        st.species_seen |= set(s.seen)
        st.species_owned |= set(s.owned)
        if not p.valid:
            return
        # Trainers beaten: their flags turned on.
        start = g.trainer_flags_start
        if p.flags and s.flags and p.flags != s.flags:
            for t in g.fightable_trainers:
                f = start + t
                if s.flag(f) and not p.flag(f):
                    st.trainers_beaten[str(t)] = st.trainers_beaten.get(str(t), 0) + 1
        b = st.battles.setdefault(name, {"wild": 0, "trainer": 0, "blackouts": 0, "trainer_losses": 0})
        if s.in_battle and not p.in_battle:
            b["trainer" if s.trainer_battle else "wild"] += 1
            self._battle = {"map": name, "trainer": s.trainer_battle,
                            "levels": [m.level for m in s.party if not m.is_egg]}
        if p.in_battle and not s.in_battle and self._battle:
            info, self._battle = self._battle, None
            if p.all_fainted:
                bb = st.battles.setdefault(info["map"], {"wild": 0, "trainer": 0, "blackouts": 0, "trainer_losses": 0})
                bb["blackouts"] += 1
                if info["trainer"]:
                    bb["trainer_losses"] += 1
                st.blackouts.append({"map": info["map"], "trainer_battle": info["trainer"],
                                     "party_levels": info["levels"],
                                     "badges": s.badge_count})

    def _maybe_pool(self, s) -> None:
        """Keep a few save states per map, so later sessions can start all over the game."""
        if not s.valid or s.in_battle or s.all_fainted or s.map_id not in self.game.maps:
            return
        d = self.pool / f"{s.map_id[0]}_{s.map_id[1]}"
        if d.exists() and len(list(d.glob("*.state"))) >= POOL_PER_MAP:
            return
        if self.rng.random() > 0.02:  # don't save on the first step in: let the map settle
            return
        d.mkdir(parents=True, exist_ok=True)
        tmp = d / f"{uuid.uuid4().hex[:10]}.tmp"
        tmp.write_bytes(gzip.compress(self.emu.save_state(), 6))  # ~400 KB raw
        tmp.replace(tmp.with_suffix(".state"))

    # --- findings -------------------------------------------------------------------

    def _capture(self, f: Finding, ring, actions, screen, clip, step) -> None:
        sig = f.signature
        self.captures[sig] = self.captures.get(sig, 0) + 1
        n = self.captures[sig]
        f.extra["occurrence"] = n
        if n > MAX_CAPTURES_PER_SIGNATURE:
            self._note(f, None)
            return
        d = self.out / "findings" / f"{f.kind}-{f.check}-w{self.worker}-{uuid.uuid4().hex[:6]}"
        d.mkdir(parents=True, exist_ok=True)
        base_step, before, idx = ring[0] if ring else (step, None, 0)
        inputs = [a.to_json() for a in actions[idx:]]
        if before is not None:
            (d / "before.state").write_bytes(before)
            (d / "inputs.json").write_text(json.dumps(inputs))
        from PIL import Image

        Image.fromarray(screen).save(d / "screenshot.png")
        if clip:
            frames = [Image.fromarray(fr) for fr in clip]
            frames[0].save(d / "clip.gif", save_all=True, append_images=frames[1:], duration=66, loop=0)
        if f.reproducible and before is not None:
            f.extra["reproduced"] = self._reproduce(f, before, inputs)
        self._note(f, d)

    def _reproduce(self, f: Finding, before: bytes, inputs) -> bool:
        """Replay the presses from the earlier state and see if the same thing happens."""
        now = self.emu.save_state()
        try:
            self.emu.load_state(before)
            return any(x.check == f.check and x.title == f.title for x in replay(self, inputs))
        except Exception:
            return False
        finally:
            self.emu.load_state(now)

    def _note(self, f: Finding, d: Path | None) -> None:
        rec = {**asdict(f), "signature": f.signature, "folder": str(d.relative_to(self.out)) if d else None,
               "worker": self.worker, "time": time.time(), "game": self.game.name, "release": self.game.release}
        with open(self.out / f"findings-w{self.worker}.jsonl", "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        if d is not None:
            (d / "finding.json").write_text(json.dumps(rec, indent=1))
        self.log(f"[{self.worker}] {f.kind}: {f.title} ({f.map})"
                 + (f" reproduced={f.extra.get('reproduced')}" if "reproduced" in f.extra else ""))


def replay(tester: Tester, inputs) -> list[Finding]:
    """Run the given presses from the emulator's current state through fresh detectors."""
    det = Detectors(tester.game)
    out = []
    for step, raw in enumerate(inputs):
        a = Action.from_json(raw)
        held = tester.do(a)
        s = tester.read()
        out += det.check(s, a.buttons, screen_hash(tester.emu.screen()), held, step, last_was_move=a.tag == "move")
    return out
