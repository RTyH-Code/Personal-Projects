# FireRed AI: the learning agent

This is the optional part of the project. The main tool is the playtester
([README](README.md)). This agent teaches itself to play Pokémon FireRed by
trial and error.

It doesn't know anything about Pokémon at the start. It presses buttons,
watches the screen, and gets small rewards when something good happens:
walking somewhere new, leveling up, catching a Pokémon or winning a badge.
Over millions of button presses it learns which actions lead to rewards.
This is **reinforcement learning**, using the PPO algorithm.

It works with vanilla FireRed (US, v1.0 or v1.1) and with the
[FireRed QoL + Hard](../firered-qol-hard/README.md) hack in this repo,
patched from either revision. You need your own ROM; none is included.

## How it works

```
             ┌──────────── observation ────────────┐
             │ • last 3 screens (grayscale, ½ size) │
 mGBA  ───▶  │ • map of tiles already explored     │  ───▶  neural net  ───▶  button
 (emulator)  │ • party HP/levels, badges, Pokédex  │        (PPO policy)
             └──────────────────────────────────────┘
      ▲                                                                       │
      └─────────────────────── press for 8 frames, wait 16 ───────────────────┘
```

- **Emulator.** [stable-retro](https://github.com/Farama-Foundation/stable-retro)'s
  built-in mGBA core. Several copies run in parallel, much faster than real time.
- **Game state.** `firered_ai/ram.py` reads the map, position, party, badges,
  Pokédex and money straight from RAM. The addresses come from the
  [pret/pokefirered](https://github.com/pret/pokefirered) decompilation.
- **Rewards.** `firered_ai/rewards.py`:

  | Event | Reward |
  |---|---|
  | Step on a new tile | 0.02 |
  | Enter a new map | 0.5 |
  | Party gains a level (beyond its best so far) | 1 |
  | Get the starter / the Pokédex | 5 each |
  | Catch a new species (one on the Pokédex goal) | 2 |
  | Earn a badge | 20 |
  | Become Champion | 100 |
  | Meet every goal (ends the run) | 200 |
  | Heal the party (full heal) | 1 |
  | Party blacks out | −2 |

  Rewards only count *new* progress, so the agent can't farm them by
  repeating something.
- **Learning.** [Stable-Baselines3](https://stable-baselines3.readthedocs.io/)
  PPO with a CNN for the images and a small MLP for the stats.

## The goal

By default the agent works towards three things:

1. **All 8 badges.**
2. **Become Champion** (enter the Hall of Fame).
3. **A complete Pokédex** for the game you're playing.

How it gets there, and in what order, is up to the agent. When all of them
are met, the episode ends with a big bonus. Choose a subset with
`--goals`, e.g. `--goals badges,champion`, or `--goals none` for open-ended
play.

### What "complete Pokédex" means

Only Pokémon one save can actually own count: no trading, no Mystery Gift.
`tools/pokedex_targets.py` worked these out from the game's source (the pret
decompilation, with your hack's patches applied). It follows wild
encounters, gifts, legendary encounters, in-game trades, the roaming
legendary, evolution (only by methods that work in this game) and Day Care
breeding.

| Game | Species for a complete Pokédex | Not obtainable in one save |
|---|---|---|
| FireRed (US v1.0 or v1.1) | 170 | LeafGreen exclusives, trade evolutions (Alakazam, Machamp, Golem, Gengar), Mew and the other event Pokémon, Espeon and Umbreon (FRLG has no clock), most of Johto and Hoenn |
| FireRed QoL + Hard (R14) | 415 (all 386 + 29 later evolutions) | none |

In vanilla, some choices lock others out for the rest of the save. Each
counts as one either/or: the starter, which also decides the roaming
legendary (Bulbasaur → Entei, Charmander → Suicune, Squirtle → Raikou),
and the Mt. Moon fossil (Omanyte or Kabuto). The QoL + Hard hack has no
such choices. The lists are in `firered_ai/data/`.
The right one is picked by recognising the ROM (see the README). Override it with
`--pokedex firered`, `--pokedex firered-qol-hard` or a JSON file.

To make a list for another hack, run the generator on its source:

```bash
python tools/pokedex_targets.py path/to/pokefirered my-hack > my-hack.json
```

### Building on progress

A full playthrough is hundreds of thousands of button presses, far longer
than one episode. So each time an agent gets further than before (new
ground, a new map, levels, a new species, a badge), its save state goes
into a **progress pool** (`runs/<name>/progress/`). 80% of episodes start
from one of the 8 best states in the pool, and the rest start from the
bedroom. Explored tiles carry over, so the agent isn't paid twice for the
same ground. Turn it off with `--no-progress-pool`, or change the mix with
`--progress-prob`.

## Setup

Python 3.10 or newer.

```bash
cd firered-ai
python -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements-learning.txt
```

On Windows, use `.venv\Scripts\activate`. stable-retro has prebuilt
packages for Linux and macOS; on Windows, use WSL.

## 1. Make a start state

Skip the title screen and Oak's intro once, so training starts in the
player's bedroom:

```bash
python make_start_state.py path/to/firered.gba states/start.state --screenshot start.png
```

This mashes through the intro with a script. It names the player and rival
"A"-something; that doesn't matter to the AI. Check `start.png` to see where
it ended up.

## 2. Train

```bash
python train.py path/to/firered.gba --state states/start.state
```

- `--envs N` runs N emulators at once (default: one per CPU core).
- `--timesteps` is the total number of button presses (default 10 million).
- `--episode-steps` is how long each attempt lasts before it restarts from
  the start state (default 8192 presses, about 50 minutes of game time).
- Ctrl+C stops and saves `runs/firered/latest.zip`. Continue with
  `--resume runs/firered/latest.zip`.
- Checkpoints go to `runs/firered/checkpoints/`. Whenever an agent wins a
  new badge, its save state is kept in `runs/firered/milestones/`.

Watch progress with TensorBoard:

```bash
tensorboard --logdir runs
```

`game/goal_progress` (0 to 1) and `goal/badges`, `goal/champion` and
`goal/pokedex` show progress towards the goal. `game/start_score` and
`game/score` show how far into the game episodes start and end up. `game/maps_explored`,
`game/level_sum` and `game/badges` show how far agents get per episode.
`rollout/ep_rew_mean` is the average reward.

## 3. Watch it play

```bash
python play.py path/to/firered.gba runs/firered/latest.zip --out play.mp4
```

Leave out the model to see random button presses for comparison. At the
end it lists which Pokémon are still missing from the Pokédex goal. Start
from a pool state with `--state runs/firered/progress/<file>.state` to
watch the furthest an agent has got.
Use `--out play.gif` if you don't have ffmpeg.

## What to expect

Pokémon is a hard game for this kind of AI: rewards are far apart and
there's a lot of text to click through. As a rough guide, based on similar
projects for Pokémon Red:

- **First ~100k presses:** wandering, mostly in the house.
- **~1M:** leaves the house, picks a starter in Oak's lab, explores
  Pallet Town and Route 1.
- **~10M+:** reaches Viridian, levels up in the tall grass, Pewter.
- Badges take tens of millions of presses and some reward tuning.
- Becoming Champion, let alone completing the Pokédex, is beyond anything
  this kind of AI has done so far. The goal gives it a direction and a way
  to measure how far it gets.

Each emulator does about 60 presses per second (each press is 24 frames),
so speed scales with CPU cores: on 4 cores, 10M presses takes roughly
12 hours. A GPU helps a little with the learning updates.

## Tuning

- **Reward weights.** Put overrides in a JSON file and pass `--rewards`:

  ```json
  {"explore": 0.05, "level": 0.5, "heal": 0}
  ```
- **Later starting points.** Any save state can be a start state. Take one
  from `runs/*/milestones/`, or one from just past a part where the agent
  gets stuck, and pass it with `--state`.
- **START button.** It's off by default because the agent tends to sit in
  menus. Turn it on with `--allow-start` once it needs items.

## Tests and files

The tests, the other-hacks notes and the list of files are in the
[README](README.md). The learning agent's own files:

| File | What it does |
|---|---|
| `train.py` | Training |
| `play.py` | Watch an agent and record video |
| `firered_ai/env.py` | The Gymnasium environment the agent plays in |
| `firered_ai/rewards.py` | Reward shaping |
| `firered_ai/goals.py` | The end goal: badges, Champion, Pokédex |
| `firered_ai/progress.py` | Progress pool: start episodes from the best states so far |
| `firered_ai/cli.py` | Shared command-line options |
