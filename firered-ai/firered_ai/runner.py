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
from .tester import Start, Tester

USER_START_SHARE = 0.35  # the rest come from the pool of states saved all over the game


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

    weights = [1.0 / (1 + seen.get(name(d), 0)) for d in pool]
    d = rng.choices(pool, weights)[0]
    f = rng.choice(sorted(d.glob("*.state")))
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


def prepare(args, log=print) -> dict:
    """Detect the game, collect start points and write config.json."""
    game, note = detect(args.rom)
    log(f"ROM: {note}")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    addresses = load_addresses(args.addresses)
    states = [str(Path(p)) for p in args.states]
    saves = [str(Path(p)) for p in args.saves]
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
        "hours": args.hours,
        "workers": args.workers,
    }
    (out / "config.json").write_text(json.dumps(config, indent=1))
    return config
