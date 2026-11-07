"""Running playtest workers in parallel and choosing where each session starts."""

from __future__ import annotations

import json
import os
import random
import time
import traceback
from pathlib import Path

from .game import Game, detect
from .ram import load_addresses
from .states import load_state_file
from .tester import Start, Tester, pool_rank

USER_START_SHARE = 0.35  # the rest come from the pool of states saved all over the game
ADVANCED_SHARE = 0.75  # of pool starts: one of the most advanced states saved (the rest: less-visited maps)
ADVANCED_TOP = 6


def load_bytes(path) -> bytes:
    return load_state_file(path)


def user_starts(config) -> list[Start]:
    out = []
    for p in config["states"]:
        out.append(Start("state", Path(p).name, load_bytes(p)))
    for p in config["saves"]:
        out.append(Start("sav", Path(p).name, Path(p).read_bytes()))
    return out


def steps_per_map(out: Path) -> dict[str, int]:
    """Presses spent on each map so far, summed over all workers."""
    total: dict[str, int] = {}
    for f in out.glob("stats-w*.json"):
        try:
            for name, n in json.loads(f.read_text())["maps"].items():
                total[name] = total.get(name, 0) + n
        except (OSError, ValueError, KeyError):
            continue
    return total


def pick_start(rng: random.Random, starts: list[Start], out: Path, game: Game) -> Start:
    pool = [d for d in (out / "pool").glob("*_*") if d.is_dir() and any(d.glob("*.state"))]
    if not pool or (starts and rng.random() < USER_START_SHARE):
        return rng.choice(starts)
    seen = steps_per_map(out)

    def name(d):
        g, n = (int(x) for x in d.name.split("_"))
        return game.map_name(g, n)

    if rng.random() < ADVANCED_SHARE:
        # Usually carry on from the furthest points reached, so the checklist moves forward.
        files = sorted((f for d in pool for f in d.glob("*.state")), key=pool_rank)[-ADVANCED_TOP:]
        f = rng.choice(files)
        return Start("pool", f"pool:{name(f.parent)}", load_state_file(f))

    # Otherwise somewhere less visited, for variety.
    weights = [1.0 / (1 + seen.get(name(d), 0)) for d in pool]
    d = rng.choices(pool, weights)[0]
    files = sorted(d.glob("*.state"), key=pool_rank)
    # Usually the most advanced state there, sometimes another for variety.
    f = files[-1] if rng.random() < 0.6 else rng.choice(files)
    return Start("pool", f"pool:{name(d)}", load_state_file(f))


def worker_main(config: dict, worker: int, stop) -> None:
    """Entry point of one worker process."""
    from .emulator import Emulator

    out = Path(config["out"])
    log_path = out / f"log-w{worker}.txt"

    def log(msg):
        with open(log_path, "a") as fh:
            fh.write(time.strftime("%H:%M:%S ") + msg + "\n")

    try:
        game = Game.load(config["game"])
        emu = Emulator(config["rom"])
        tester = Tester(emu, game, out, worker, seed=config["seed"] + worker,
                        addresses=load_addresses(config.get("addresses")), log=log, stop=stop)
        starts = user_starts(config)
        rng = random.Random(config["seed"] * 1000 + worker)
        while not stop.is_set():
            start = pick_start(rng, starts, out, game)
            tester.session(start, config["session_steps"])
            tmp = out / f"stats-w{worker}.tmp"
            tmp.write_text(json.dumps(tester.stats.to_json()))
            tmp.replace(out / f"stats-w{worker}.json")
    except Exception:
        log("worker crashed:\n" + traceback.format_exc())
        raise


def make_new_game_states(rom: str, game: Game, rule_sets: list[list[str]], out: Path, addresses, log=print) -> list[str]:
    """Start states for new games, one per set of challenge rules."""
    from .bootstrap import skip_intro
    from .emulator import Emulator

    emu = Emulator(rom)
    paths = []
    for rules in rule_sets:
        label = "+".join(rules) or "plain"
        log(f"Making a new-game start state ({label})...")
        emu.load_state(emu.power_on)
        if not skip_intro(emu, game, rules, addresses, log=None):
            log(f"  couldn't get through the new-game setup for {label}; skipping it")
            continue
        p = out / "starts" / f"new-game-{label}.state"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(emu.save_state())
        paths.append(str(p))
    emu.close()
    return paths


def run(config: dict, hours: float, workers: int, report_every: float = 300, log=print) -> Path:
    import multiprocessing as mp

    from .report import write_report

    out = Path(config["out"])
    ctx = mp.get_context("spawn")
    stop = ctx.Event()
    procs = [ctx.Process(target=worker_main, args=(config, w, stop), daemon=True) for w in range(workers)]
    for p in procs:
        p.start()
    deadline = time.time() + hours * 3600
    next_report = time.time() + min(report_every, 60)
    try:
        while time.time() < deadline and any(p.is_alive() for p in procs):
            time.sleep(min(10, max(0.1, deadline - time.time())))
            if time.time() >= next_report:
                write_report(out)
                next_report = time.time() + report_every
    except KeyboardInterrupt:
        log("Stopping...")
    stop.set()
    for p in procs:
        p.join(timeout=60)
        if p.is_alive():
            p.terminate()
    report = write_report(out)
    dead = [w for w, p in enumerate(procs) if p.exitcode not in (0, None, -15)]
    if dead:
        log(f"Workers {dead} crashed; see log-w*.txt in {out}")
    return report


def latest_run(runs: Path, exclude: Path | None = None) -> Path | None:
    """The most recent run folder that got far enough to leave something to carry on from."""
    found = []
    for d in Path(runs).iterdir() if Path(runs).is_dir() else []:
        if not d.is_dir() or (exclude is not None and d.resolve() == Path(exclude).resolve()):
            continue
        if (d / "config.json").exists() and (any(d.glob("furthest/*.state")) or (d / "pool").is_dir()):
            found.append(d)
    return max(found, key=lambda d: (d / "config.json").stat().st_mtime, default=None)


def carry_on(previous: str, out: Path, log=print) -> tuple[list[str], str]:
    """Start a run where an earlier one got to.

    Copies the earlier run's pool of save states (one to three per map it
    reached) and adds each worker's furthest point as a start of its own.
    `previous` is a run folder, or "latest" for the newest one next to `out`.
    Returns the new start states and the name of the run carried on from.
    """
    import shutil

    prev = latest_run(out.parent, exclude=out) if previous == "latest" else Path(previous)
    if prev is None or not prev.is_dir():
        raise SystemExit(f"No earlier run to carry on from ({previous}).")
    log(f"Carrying on from {prev.name}.")
    pool = prev / "pool"
    if pool.is_dir():
        for d in pool.iterdir():
            if d.is_dir():
                shutil.copytree(d, out / "pool" / d.name, dirs_exist_ok=True)
    starts = []
    for f in sorted(prev.glob("furthest/w*.state")):
        try:
            info = json.loads(f.with_suffix(".json").read_text())
            label = f"carry-on-{info['badges']}badges-{info['map']}-{f.stem}"
        except (OSError, ValueError, KeyError):
            label = f"carry-on-{f.stem}"
        dest = out / "starts" / f"{label}.state"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, dest)
        starts.append(str(dest))
    if not starts and not (out / "pool").is_dir():
        raise SystemExit(f"{prev} has nothing to carry on from (no furthest points or pool).")
    maps = len(list((out / "pool").glob("*_*")))
    log(f"  {len(starts)} furthest point{'' if len(starts) == 1 else 's'} and saves from "
        f"{maps} map{'' if maps == 1 else 's'}.")
    return starts, prev.name


def prepare(args, log=print) -> dict:
    """Detect the game, collect start points and write config.json."""
    game, note = detect(args.rom)
    log(f"ROM: {note}")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    addresses = load_addresses(args.addresses)
    states = [str(Path(p)) for p in args.states]
    saves = [str(Path(p)) for p in args.saves]
    continued_from = None
    if getattr(args, "continue_from", None):
        more, continued_from = carry_on(args.continue_from, out, log)
        states += more
    if args.new_games is not None:
        rule_sets = [[r for r in rs.split(",") if r and r != "plain"] for rs in args.new_games]
        if "HACK_NUZLOCKE" not in game.flags and any(rule_sets):
            log("This game has no challenge rules; making one plain new game instead.")
            rule_sets = [[]]
    elif not states and not saves:
        rule_sets = [[], ["nuzlocke", "level_caps"], ["no_items", "set_style", "exp_share"]] \
            if "HACK_NUZLOCKE" in game.flags else [[]]
    else:
        rule_sets = []
    if rule_sets:
        states += make_new_game_states(args.rom, game, rule_sets, out, addresses, log)
    if not states and not saves:
        raise SystemExit("No start points: give --states or --saves, or check that the new-game setup works "
                         "(python make_start_state.py ROM out.state --screenshot shot.png).")
    config = {
        "rom": os.path.abspath(args.rom),
        "game": game.name,
        "rom_note": note,
        "states": [os.path.abspath(p) for p in states],
        "saves": [os.path.abspath(p) for p in saves],
        "out": str(out.resolve()),
        "session_steps": args.session_steps,
        "seed": args.seed,
        "addresses": args.addresses,
        "started": time.time(),
        "continued_from": continued_from,
        "hours": args.hours,
        "workers": args.workers,
    }
    (out / "config.json").write_text(json.dumps(config, indent=1))
    return config
