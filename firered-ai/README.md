# FireRed Playtester

An unattended playtester for [FireRed QoL + Hard](../firered-qol-hard/README.md)
(and vanilla Pokémon FireRed). Leave it running overnight: it plays the real
patched ROM in several emulators at once, goes everywhere it can, and
writes a report of anything that went wrong, with a save state and a video
for each problem.

It's a bug hunter, not a second you. It can't tell you whether something is
fun, read text for typos, or know that a change was intended. It battles
with simple rules, so it wins easy fights and loses hard ones. That makes
its blackout numbers a pointer to difficulty spikes, not a verdict.

There's also an optional [learning agent](LEARNING.md) that teaches itself
to play with reinforcement learning. The playtester doesn't need it.

## What it checks

After every button press it reads the game's memory and checks:

| Kind | What it catches |
|---|---|
| **Crash** | The game stops reading the buttons (its main loop died or hung). |
| **Softlock** | The screen doesn't change at all for ~6 minutes of pressing everything, or the player can't move from one spot for ~25 minutes. |
| **Corrupt data** | Bad Eggs (a Pokémon's encrypted data doesn't match its checksum), impossible species, levels, HP or stats, Exp. overflow, a level or Exp. going down, money over 999,999, broken bag slots, being on a map that doesn't exist, more than 6 in the party. |
| **Rule broken** | A Pokémon levels past the level cap. With Nuzlocke on: a fainted Pokémon gets HP back, or a second catch happens in a used area. With "no items in battle" on: a bag item gets used in battle. |

Data that could be read halfway through the game writing it has to stay
wrong for two presses in a row before it counts.

It also keeps **coverage** (maps visited, trainers beaten, species seen
and caught) and **difficulty** numbers (battles and blackouts per map).

## How it plays

- **Exploring:** it heads for ground it hasn't stood on, finds its way back
  to unfinished spots, and leaves maps through exits toward the places
  visited least. When a step doesn't move it, it presses B (in case text is
  open) and tries again. Then it presses A at the obstacle, which talks to
  people, reads signs, picks up items and uses HM obstacles.
- **Menus:** now and then it opens the START menu and pokes around (bag,
  party, the Nuzlocke tracker, options, saving...).
- **Battles:** mostly FIGHT, with random menu moves so the bag, switching
  and RUN get used too. In wild battles it sometimes throws a Poké Ball.
- **Covering the whole game:** while it plays it keeps a few save states on
  every map it reaches. Later sessions start from those, favouring the
  least-visited maps. Give it your own saves to reach later content sooner.

## Install on Windows (one click)

The playtester runs inside WSL, the Linux system built into Windows 10 and
11. The installer sets all of that up for you.

1. **Get the files.** On this repository's GitHub page, click the green
   **Code** button, then **Download ZIP**. Right-click the downloaded file,
   choose **Extract All...**, and extract it somewhere easy, like your
   Documents folder.
2. **Run the installer.** In the extracted folder, open `firered-ai`, then
   `install`, and double-click **`Install.bat`**. Run it from there: don't
   move the `install` folder elsewhere, because it copies the playtester
   from the folder around it.
   - If Windows says "Windows protected your PC", click **More info**, then
     **Run anyway**. It's a script you downloaded yourself, so Windows is
     being careful.
   - **The first time only:** it needs administrator permission (click
     **Yes**) to install WSL and Ubuntu. That downloads about 1 GB. Restart
     if Windows asks. An **Ubuntu** window then asks you to choose a
     username and password. They're only for Ubuntu, so pick anything you'll
     remember. Nothing appears while you type the password; that's normal.
     When it shows a line ending in `$`, close that window and
     **double-click `Install.bat` again**.
   - It then installs Python and the playtester and runs its self-check,
     which takes a few minutes. When it says **All set!**, you're done.
3. **Two shortcuts appear on your desktop:**
   - **FireRed Playtest** starts a run. Double-click it and pick your
     patched ROM, or drag the `.gba` file onto it. It asks how many hours to
     play (just press Enter for 8). It also asks for an optional folder of
     your `.sav` files, so it can test later parts of the game: drag the
     folder into the window and press Enter.
   - **FireRed Playtest Reports** opens the folder of past runs. Open
     `report.html` in a run's folder to see the results.

While a run goes on, leave its window open. Closing it stops the run. Your
PC stays awake until the run ends (the screen can still turn off), and the
report opens by itself at the end.

**Updating:** download the ZIP again and double-click `Install.bat`. It
updates the playtester and keeps your past runs.

## Install on Linux or a Mac

On Linux or an Apple Silicon Mac, `bash install/setup.sh` does the same
setup in `~/firered-playtester`. Then start a run with:

```bash
bash ~/firered-playtester/install/run.sh path/to/rom.gba 8
```

## Manual setup

If you'd rather set it up by hand: in Ubuntu (WSL) on Windows, or a terminal
on Linux or an Apple Silicon Mac, with Python 3.10 or newer:

```bash
cd ~/Personal-Projects/firered-ai
```

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

That installs only the emulator, numpy and Pillow. PyTorch is only needed
for the learning agent.

## Run it

```bash
python playtest.py ~/roms/FireRed-QoL-Hard.gba --hours 8
```

By default it starts three new games, one per set of challenge rules:
none; Nuzlocke + level caps; and no items + Set style + party Exp. Share.
It gets through the intro and the challenge menu itself. It uses all CPU
cores but one, and writes everything to `runs/playtest-<date>/`.

**Start from your own saves** to test later parts of the game. mGBA keeps a
game's battery save next to the ROM as a `.sav` file:

```bash
python playtest.py ~/roms/FireRed-QoL-Hard.gba --hours 8 --saves ~/saves/*.sav
```

The playtester boots each save and picks CONTINUE. Saves from all through
the game work best: one before each gym, the Elite Four, the Sevii Islands
and so on. You can also pass save states with `--states`, or choose the
new games with `--new-games plain nuzlocke,level_caps`. The rules are
`nuzlocke`, `level_caps`, `no_items`, `set_style` and `exp_share`.

Other options: `--workers N`, `--session-steps` (presses before it jumps to
a new start point, default 2500), `--out DIR`. Stop early with Ctrl+C; the
report is written either way.

## Read the report

Open `report.html` in the run folder. On WSL, `explorer.exe runs` opens the
folder in Windows. It refreshes every 5 minutes while the run goes on.

- **Problems found:** the worst first, with how often each happened and a
  screenshot. Click it for a clip of the ~40 seconds before.
  "Reproduced: yes" means the playtester re-ran the same presses from a
  save state shortly before, and the problem happened again.
- **Possible difficulty spikes:** maps where it blacked out at least 3 times,
  in a quarter or more of its battles there.
- **Coverage:** the maps it hasn't reached yet, and where sessions started.

Each problem's folder in `findings/` holds:

| File | |
|---|---|
| `finding.json` | What happened, where, and whether it reproduced |
| `before.state` | A save state from 50–150 presses before. It's mGBA's own format, so try mGBA's *File → Load State File* |
| `inputs.json` | Every press from `before.state` to the problem |
| `screenshot.png`, `clip.gif` | What it looked like |

To watch it happen again and get a full-speed GIF:

```bash
python replay.py ~/roms/FireRed-QoL-Hard.gba runs/playtest-.../findings/<folder> --out replay.gif
```

## Speed

Each worker runs one emulator flat out, much faster than real time. The
report's header shows how many presses and hours of play a run managed. On
the small test ROM each worker did about 115 presses a second; FireRed
itself will be slower.

## New hack releases

The playtester recognises the hack by the "QoL+HARD R14" text its Options
screen shows, so new releases still work. Some of what it knows comes from
the hack's source: maps, trainers, level caps, the flags for the challenge
rules, and the save layout. If a release changes those, it warns at the
start. To update it, apply the patches to pret/pokefirered and regenerate:

```bash
git clone https://github.com/pret/pokefirered && cd pokefirered && git checkout ce6406d
```

```bash
git am ../Personal-Projects/firered-qol-hard/source-patches/*.patch && cd -
```

```bash
python tools/game_data.py ../pokefirered firered_qol_hard > firered_ai/data/games/firered_qol_hard.json
```

```bash
python tools/pokedex_targets.py ../pokefirered firered-qol-hard > firered_ai/data/pokedex_firered_qol_hard.json
```

A test, `test_profiles_match_the_hack_in_this_repo`, fails when the hack's
`.bps` patches are a newer release than this data, as a reminder.

## Tests

```bash
pip install pytest
```

```bash
python -m pytest tests
```

The tests need no ROM. They use a fake emulator that models FireRed's
memory (including encrypted Pokémon data and the challenge menu), plus a
tiny hand-assembled GBA ROM run on the real mGBA core.

## Files

| File | What it does |
|---|---|
| `install/Install.bat` | One-click Windows installer (`install.ps1`, which runs `setup.sh` inside Ubuntu) |
| `install/Playtest.bat` | Windows launcher behind the desktop shortcut (`playtest.ps1`, which runs `run.sh`) |
| `playtest.py` | Run the playtester |
| `replay.py` | Replay a finding |
| `make_start_state.py` | Make a new-game save state, with challenge rules |
| `firered_ai/tester.py` | One worker: sessions, captures, replays |
| `firered_ai/detectors.py` | The bug checks |
| `firered_ai/explorer.py` | What to press |
| `firered_ai/runner.py` | Workers, start points, the shared pool |
| `firered_ai/report.py` | `report.html` and `summary.json` |
| `firered_ai/game.py` | Recognising the ROM; what's known about it |
| `firered_ai/ram.py` | Reading the game's memory, including encrypted Pokémon data |
| `firered_ai/bootstrap.py` | Getting through the intro, challenge menu, or a save's title screen |
| `firered_ai/emulator.py` | mGBA via stable-retro, including loading battery saves |
| `firered_ai/data/games/` | Game profiles for FireRed and FireRed QoL + Hard |
| `tools/game_data.py` | Make a game profile from pret source |
| `tools/pokedex_targets.py` | Work out which Pokémon a game lets you own |
| `tools/symbols_from_map.py` | RAM addresses for hacks that move things around |
