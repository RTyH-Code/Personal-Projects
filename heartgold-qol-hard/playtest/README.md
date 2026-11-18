# HeartGold playtesters

Three unattended testers for [HeartGold QoL + Hard](../README.md). All play
the real game in an emulator on a test build of the hack.

- `battle_test.py` fights trainers and reports which battles were won, lost
  or never finished.
- `walk_test.py` goes to every map, to every legendary the hack adds and
  into the grass of every area, and uses the hack's new features. See
  [The overworld tester](#the-overworld-tester).
- `story_bot.py` plays the story from the bedroom on. So far it gets as far
  as Falkner's badge. See [The story bot](#the-story-bot).

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
It also short-cuts three story steps the testers can't take, in the test
build only: Snorlax wakes without the Poké Flute on the radio, the Union Cave
Lapras stays still instead of swimming about, and the harness can release
Latias and Latios to roam. The Pokémon and the battles themselves are left
as they are.

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

It has nine tests. The first four run by default; name one or more after `out` to choose.

| Test | What it does |
|---|---|
| `sweep` | Warps to every map and checks that it loads and that the player can take a step. "scene" means a trainer or a story scene started first, which also shows the map works. |
| `legendaries` | Goes to each legendary the hack adds, at its real place. With its story gate closed it must not be there. With the gate open, talking to it from every side a player can stand on must start a battle with the right Pokémon at the right level. |
| `wild` | On every map with wild Pokémon on land, walks in the grass or cave until three appear, and checks each one's species and level against the hack's encounter tables. |
| `features` | Has the Ruins of Alph scientist revive an Old Amber, buys every item on the counters the hack restocks and on an ordinary Poké Mart counter at different badge counts, checking the price paid for each, and uses Surf from the bag. |
| `surf` | Uses Surf from the bag on every map with Pokémon in the water, surfs until three appear and checks them against the tables. |
| `headbutt` | Headbutts trees on every map that has them, with a lead Pokémon that knows the move, and checks what falls out. |
| `statics` | Meets the game's own static Pokémon whose level the hack changes. |
| `fish` | Fishes with each rod, used from the bag, on every map with Pokémon to fish for, and checks the catch against the tables. Slow: the bag only draws properly at normal speed. |
| `roamers` | Releases Latias and Latios as Steven does, checks both are made at their level, moves them onto Route 1 (in memory, as waiting for them to wander there takes hours) and walks its grass until one appears. |

Results go to `out/walk_results.json`; anything that isn't "ok" gets a
screenshot in `out`. `--maps CODE,CODE` limits a run to some maps.

## Results so far

| Test | Result |
|---|---|
| `sweep` | 540 maps: 462 load and can be walked on, 49 start a trainer battle or story scene first, 24 are not maps a player walks on (no events, or nowhere to stand), and 5 load but the player could not step: the four Elite Four rooms and one S.S. Aqua map. Those five are unchanged from the original game; in the two looked at, the game moves the player as they arrive, so the test never gets a normal step. |
| `legendaries` | All 21 are absent with their gate closed and start the right battle with it open, from every side. |
| `wild` | 111 maps: on 103, all three Pokémon met were in the table at the right level. On 4 a trainer stopped the walk (Routes 15 and 27, National Park, Mt. Moon). The other 4 are the Ruins of Alph hall and its copies, where nothing appeared; the Unown there depend on the puzzles. |
| `features` | The reviver gave an Aerodactyl. Every counter sold exactly the expected list at each badge count, and every item cost its listed price: the evolution shop (24 items with no badges, 33 with sixteen), the berry stand (14, 18 and 40 with none, four and sixteen), the held item counter (23, with Rare Candy, Ability Capsule and Ability Patch) and a Poké Mart at 0, 2, 4, 6 and 8 badges. Surf from the bag worked. |
| `surf` | 72 maps have Pokémon in the water. On 61, all three met were in the table at the right level. 7 have no shore the test can start from, and on 4 the test player left the water or could not start; none of those says anything about the game. |
| `headbutt` | 60 maps have trees. On 59 everything that fell out was in the table at the right level, including the Kanto trees at their post-game levels. One map has no tree the test can stand beside. |
| `statics` | All ten are at their new levels: Articuno, Zapdos, Moltres (65), Suicune (60), Kyogre (70), Mewtwo (80), the red Gyarados (34), Sudowoodo (22), Snorlax (65), and Lapras (22, on a Friday, tested by setting the emulator's clock). |
| `fish` | 71 maps have a rod table. On 36, everything caught was in the table at the right level. 6 have no water (their table is shared with another floor) and 1 has no water's edge to stand on. On the other 28 nothing bit, or the run did not reach them: on Kanto routes with grass almost nothing ever bites under the test, and the unmodified game behaves the same on Route 22, so this is a limit of how the test fishes, not something the hack changed. |
| `roamers` | Latias and Latios are both made at Lv. 60, and Latios was met at Lv. 60 in the grass of Route 1. |

Other things checked by hand in the emulator: a Lucky Egg gives exactly one
and a half times the experience against the same trainer; an Ability Patch
gave Typhlosion Flash Fire, its hidden ability, and an Ability Capsule
changed Golem from Sturdy to Rock Head; a Lv. 36 Kadabra given a Rare Candy
became an Alakazam, and a Metal Coat used from the bag turned Onix into
Steelix; a save made in v0.1 loads in v0.2, both one from the very start
and one from mid-game (in Goldenrod with eight badges and a full team); the rumor collector's message
was read in all four story states.

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

# The story bot

`story_bot.py` plays the story itself, in order, from the player's bedroom.
It walks every step, takes every scene, phone call and forced battle, and
fights every trainer that spots it. The one help it gets is a team: at the
bedroom PC the harness gives it four Lv. 16 Pokémon (the battle tester's
reference families: Quilava, Flaaffy, Geodude and Kadabra), so it doesn't
have to catch and train. Its own starter from Professor Elm joins them, and
the Mystery Egg fills the last slot.

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 playtest/story_bot.py /path/to/test/hg-engine/test.nds /path/to/test/hg-engine /path/to/dumped/hg-engine out
```

How it plays:

- **Finding its way:** it plans paths on the maps' collision data, with
  ledges jumped one way only and water left alone, and a route planner picks
  the warps (doors, stairs, ladders, gatehouses) that lead to the next map.
  It reads which map the player is on, and where each person stands, from
  the game's memory.
- **Scenes:** it presses through messages and story scenes until the player
  can move again, closes the Pokégear after a phone call, and on a naming
  screen types a name and confirms it.
- **Battles:** the game's own trainer AI plays the player's side. When a
  battle opens, every battler is given its controller (overlay 12,
  `0x02260EA4`): the player's reads the touch screen, every other battler's
  runs the trainer AI with its trainer's AI flags. The bot copies an
  opponent's AI controller onto the player's battlers and gives the player
  the AI flags every trainer in the hack has, bosses included
  (`F_PRIORITIZE_SUPER_EFFECTIVE | F_EVALUATE_ATTACKS | F_EXPERT_ATTACKS`).
  So the game chooses the player's moves, and its replacement when one
  faints, exactly as it does for Falkner. The AI can't answer "Will you
  switch your Pokémon?", so the bot plays with the Set battle style, as a
  player may choose in Options. Should a battle menu still show, the bot
  falls back to the first move and the next healthy Pokémon; `story.json`
  counts the AI's moves and any menus touched.

The story is a list of stages in `story.py`. After each stage the bot saves a
save state (`out/stage_NAME.dst`), so `--from NAME` starts a later run from
there and `--until NAME` stops after it. Key stages check that the story flag
they should set is set (the starter, the Pokégear, the Pokédex, the Sprout
Tower Elder, Falkner's TM, the Mystery Egg, Proton, Bugsy's TM). When the bot gets stuck, or a check fails, it
stops and writes `out/stuck.png`, `out/stuck.dst` and the reason; results go
to `out/story.json`.

## Stages so far

From the bedroom: Mom's scene, Elm's lab and the starter, the Pokégear from
Mom, Routes 29 and 30 and Cherrygrove City (with the Guide Gent's tour) to
Mr. Pokémon's house for the Pokédex, Elm's phone call, the rival battle in
Cherrygrove, the police scene in the lab, Lyra's catching lesson, Routes 30
and 31 to Violet City, Sprout Tower to the Elder, and Falkner's gym.

Then the Mystery Egg from Elm's aide in the Violet Poké Mart (needed: a man
on Route 32 turns the player back without it, and the aide won't give it to
a full party), Route 32, Union Cave and Route 33 to Azalea Town, Kurt, the
Slowpoke Well to Proton (needed: until then a Grunt blocks the gym door), a
heal at the Pokémon Center, and Bugsy's gym. The gym's Spinarak carts are
played from the route table in the decompiled gym code: stop 0 up to the
middle floor, stop 7 to the top floor's left section, switch 0, back down to
the middle floor's left section, switch 1, then stop 6 to Bugsy.

Bugsy can beat the bot: two of the three runs with the AI lost in his gym,
the first of them without a heal beforehand.
