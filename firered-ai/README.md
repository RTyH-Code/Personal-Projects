# FireRed AI

An AI that teaches itself to play Pokémon FireRed by trial and error.

It doesn't know anything about Pokémon at the start. It presses buttons,
watches the screen, and gets small rewards when something good happens:
walking somewhere new, leveling up, catching a Pokémon or winning a badge.
Over millions of button presses it learns which actions lead to rewards.
This is **reinforcement learning**, using the PPO algorithm.

It works with vanilla FireRed (US, v1.0) and with the
[FireRed QoL + Hard](../firered-qol-hard/README.md) hack in this repo.
You need your own ROM; none is included.

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
  | Catch a new species | 2 |
  | Earn a badge | 20 |
  | Heal the party (full heal) | 1 |
  | Party blacks out | −2 |

  Rewards only count *new* progress, so the agent can't farm them by
  repeating something.
- **Learning.** [Stable-Baselines3](https://stable-baselines3.readthedocs.io/)
  PPO with a CNN for the images and a small MLP for the stats.

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
pip install -r requirements.txt
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

`game/maps_explored`, `game/level_sum` and `game/badges` show how far the
agents get per episode. `rollout/ep_rew_mean` is the average reward.

## 3. Watch it play

```bash
python play.py path/to/firered.gba runs/firered/latest.zip --out play.mp4
```

Leave out the model to see random button presses for comparison.
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

## Other hacks

If a hack moves things around in RAM, build it with pret's tools and pull
the addresses from the linker map:

```bash
python tools/symbols_from_map.py pokefirered.map > addresses.json
```

Then pass `--addresses addresses.json` to every script. The QoL + Hard
hack doesn't need this: its only new RAM comes after everything the AI
reads.

## Tests

```bash
pip install pytest
```

```bash
python -m pytest tests
```

The tests don't need a ROM. `tests/test_emulator.py` builds a tiny GBA ROM
that fakes FireRed's RAM and runs it on the real mGBA core.

## Files

| File | What it does |
|---|---|
| `firered_ai/emulator.py` | Runs the ROM in mGBA via stable-retro |
| `firered_ai/ram.py` | Reads the game state from RAM |
| `firered_ai/rewards.py` | Reward shaping |
| `firered_ai/env.py` | The Gymnasium environment the agent plays in |
| `firered_ai/bootstrap.py` | Scripted intro skip |
| `firered_ai/maps.py` | Map names (from pret/pokefirered) |
| `train.py` | Training |
| `play.py` | Watch an agent and record video |
| `make_start_state.py` | Create the start save state |
| `tools/symbols_from_map.py` | RAM addresses for other hacks |
