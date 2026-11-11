# HeartGold battle playtester

An unattended battle tester for [HeartGold QoL + Hard](../README.md). It
fights trainers in the real game, in an emulator, and reports which battles
were won, lost or never finished.

It is a first stage. It does not walk the overworld, so it can't find
broken maps, scripts or warps; it tests what a battle needs: that the
trainer's team loads, that the fight runs to the end, and roughly how hard
it is.

## How it works

1. `make_harness.py` adds a test-only script to a built copy of the hack.
   It replaces the PC in the player's bedroom with a script that gives the
   player up to six Pokémon and starts a battle against any trainer, all
   read from script variables.
2. `battle_test.py` runs that test ROM in py-desmume. For each trainer it
   loads a save state taken in the bedroom, writes the party and the
   trainer's number into those variables through the emulator's memory,
   presses A at the PC and plays the battle by reading the screen.

The test ROM is for testing only. The harness is never part of a release.

## The reference party

Every trainer is fought with the same six families, evolved as far as
their level allows, all at the level of the trainer's strongest Pokémon:
the Cyndaquil, Mareep, Geodude, Magikarp and Abra lines and Heracross.
Each has a sensible moveset picked from its level-up moves and the game's
TMs, and holds the item that boosts its first type. They have random IVs
and natures and no EVs. The tester always picks each Pokémon's strongest
move and sends in the next Pokémon when one faints. It never switches,
heals or uses items, and it doesn't look at type matchups.

That makes it a plain yardstick, not a good player: a human with a planned
team, items and switching will do much better. Read the results as a
ranking of which fights are harder than others, and as a check that every
fight works.

## Running it

You need the test tree's build requirements, py-desmume, and a vanilla
script dump (see `tools/hack/fossil_reviver.py` in the source patches).

```bash
python3 playtest/make_harness.py /path/to/dumped/hg-engine /path/to/test/hg-engine
```

Then run `make` in the test tree, and:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 playtest/battle_test.py /path/to/test/hg-engine/test.nds /path/to/test/hg-engine out --bosses --jobs 4
```

- `--bosses` (the default) fights the Gym Leaders, Elite Four, Champion,
  rival, Red, Team Rocket executives and Kimono Girls. `--all` fights every
  single-battle trainer. Trainer numbers can be listed instead.
- `--level-offset -3` makes the reference party three levels lower than the
  trainer's strongest Pokémon.
- `--jobs N` runs N emulators at once.

Results go to `out/results.json`. A battle that doesn't end within 25
minutes of game time is reported as stuck, with a screenshot.

## Limits

- One battle per trainer per run, and battles are random, so a close fight
  can go either way between runs.
- Double battles and tag battles are skipped.
- A battle takes about a minute and a half of real time.
