# HeartGold playtesters

Two unattended testers for [HeartGold QoL + Hard](../README.md). Both play
the real game in an emulator on a test build of the hack.

- `battle_test.py` fights trainers and reports which battles were won, lost
  or never finished.
- `walk_test.py` goes to every map, to every legendary the hack adds and
  into the grass of every area, and uses the hack's new features. See
  [The overworld tester](#the-overworld-tester).

Neither plays the story from start to finish, so neither proves that the
game can be completed.

# The battle tester

It tests what a battle needs: that the trainer's team loads, that the fight
runs to the end, and roughly how hard it is.

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

## Results so far

All bosses were fought three times: with the reference party at the boss's
level, five levels above and ten levels above (76 battles each).

- Every battle ran to its end. No boss team failed to load or hung.
- The party won 18, 22 and 29 of 76.
- Up to Whitney it wins at equal level, except against Bugsy.
- From Morty to Pryce it needs five to ten extra levels. Jasmine beat it
  even at ten levels above.
- Proton and Petrel in the Radio Tower lost to it at every level, so they
  were weaker than the fights around them. Both teams were strengthened
  afterwards: Proton has a fifth Pokémon, and Petrel loses
  only after knocking out four or five of the six.
- From Clair onwards it loses nearly everything even at ten levels above.
  The tester is too simple to rank those fights against each other.

## Limits

- One battle per trainer per run, and battles are random, so a close fight
  can go either way between runs.
- Double battles and tag battles are skipped.
- A battle takes about a minute and a half of real time.

# The overworld tester

`walk_test.py` starts every check from the same save state in the player's
bedroom. The harness gives a level 100 party, badges, money and items and
warps the player to a chosen tile of a chosen map. The tester then presses
buttons and reads the player's position, the Pokémon the game creates and
the items it adds to the bag straight from the emulator's memory.

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 playtest/walk_test.py /path/to/test/hg-engine/test.nds /path/to/test/hg-engine /path/to/dumped/hg-engine out --jobs 4
```

It has seven tests. The first four run by default; name one or more after `out` to choose.

| Test | What it does |
|---|---|
| `sweep` | Warps to every map and checks that it loads and that the player can take a step. "scene" means a trainer or a story scene started first, which also shows the map works. |
| `legendaries` | Goes to each legendary the hack adds, at its real place. With its story gate closed it must not be there. With the gate open, talking to it from every side a player can stand on must start a battle with the right Pokémon at the right level. |
| `wild` | On every map with wild Pokémon on land, walks in the grass or cave until three appear, and checks each one's species and level against the hack's encounter tables. |
| `features` | Has the Ruins of Alph scientist revive an Old Amber, buys every item on the counters the hack restocks and on an ordinary Poké Mart counter at different badge counts, checking the price paid for each, and uses Surf from the bag. |
| `surf` | Uses Surf from the bag on every map with Pokémon in the water, surfs until three appear and checks them against the tables. |
| `headbutt` | Headbutts trees on every map that has them, with a lead Pokémon that knows the move, and checks what falls out. |
| `statics` | Meets the game's own static Pokémon whose level the hack changes. |

Results go to `out/walk_results.json`; anything that isn't "ok" gets a
screenshot in `out`. `--maps CODE,CODE` limits a run to some maps.

## Results so far

| Test | Result |
|---|---|
| `sweep` | 540 maps: 462 load and can be walked on, 49 start a trainer battle or story scene first, 24 are not maps a player walks on (no events, or nowhere to stand), and 5 load but the player could not step: the four Elite Four rooms and one S.S. Aqua map. Those five are unchanged from the original game; in the two looked at, the game moves the player as they arrive, so the test never gets a normal step. |
| `legendaries` | All 21 are absent with their gate closed and start the right battle with it open, from every side. |
| `wild` | 111 maps: on 103, all three Pokémon met were in the table at the right level. On 4 a trainer stopped the walk (Routes 15 and 27, National Park, Mt. Moon). The other 4 are the Ruins of Alph hall and its copies, where nothing appeared; the Unown there depend on the puzzles. |
| `features` | The reviver gave an Aerodactyl. Every counter sold exactly the expected list at each badge count, and every item cost its listed price: the evolution shop (24 items with no badges, 33 with sixteen), the berry stand (14, 18 and 40 with none, four and sixteen), the held item counter (23, with Rare Candy, Ability Capsule and Ability Patch) and a Poké Mart at 0, 2, 4, 6 and 8 badges. Surf from the bag worked. |
| `surf` | 72 maps have Pokémon in the water. On 39, all three met were in the table at the right level. 29 have no shore the test can start from, and on 4 the test player left the water or could not start; none of those says anything about the game. |
| `headbutt` | 60 maps have trees. On 59 everything that fell out was in the table at the right level, including the Kanto trees at their post-game levels. One map has no tree the test can stand beside. |
| `statics` | Articuno, Zapdos, Moltres, Suicune (65, 65, 65, 60), Kyogre (70), Mewtwo (80) and the red Gyarados (34) are at their new levels. Lapras needs a Friday, and Snorlax and Sudowoodo were not found by the test. |

Other things checked by hand in the emulator: a Lucky Egg gives exactly one
and a half times the experience against the same trainer; a save made in
v0.1 loads in v0.2; the rumor collector's message was read in all four
story states.

The first run found one real problem. Cresselia stood just inside the south
gap of the Mt. Moon Square fence, where it could not be talked to from the
gap and blocked that way in. It was moved one tile up, to the edge of the
pond.

## Limits

- The save is a fresh one apart from what the harness gives, so story
  scenes and trainers behave as on a first visit. Maps where one of them
  stops the player are reported as "scene" or "interrupted", not as
  broken.
- Wild Pokémon are only sampled on land. Surfing, fishing, Rock Smash and
  Headbutt encounters are not walked into.
- It does not talk to people, read signs or pick up items.
- It runs the emulator with most frames skipped. Saving the game does not
  finish in that mode, which is the emulator and not the game: at normal
  speed a save completes in a few seconds.
- The legendary gates are opened by setting their flags, not by beating
  the Champion or Red.
