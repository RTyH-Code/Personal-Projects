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
fights every trainer that spots it. The one help it gets is its teams, so
it doesn't have to catch and train:

- From the bedroom to Violet City it uses four Lv. 16 Pokémon the harness
  gives at the bedroom PC (the battle tester's reference families: Quilava,
  Flaaffy, Geodude and Kadabra), with its starter from Professor Elm.
- Before each boss it heals at the Pokémon Center and swaps its party for
  that boss's set, which it then carries on until the next boss.

## Boss team sets

`team_sets.py` holds one set per boss: the team a player could reasonably
have by then. Run it to check every set and print the moves:

```bash
python3 playtest/team_sets.py /path/to/test/hg-engine /path/to/dumped/hg-engine
```

- **Pokémon:** caught by walking (later also with the Old Rod and from
  Headbutt trees) on the maps the story has passed, in the hack's
  encounter tables, or the starter; evolved by level up to the set's level.
  The check proves this for every Pokémon of every set.
- **Moves:** the hack's boss team tool chooses them (the best move of each
  of its types, a coverage move, a status or set-up move), but only from
  level-up moves and the TMs the player can have found by then.
- **Level:** the boss's strongest Pokémon's level.
- **EVs:** what a player who battles a lot but never trains on purpose might
  have: 128 in all at no badges, 64 more for each badge, 510 from six
  badges; half in the stat it attacks with, half in Speed. IVs are all 15
  and natures neutral, so runs can be repeated.
- **Items:** Oran Berries for now.
- **For a matchup:** a set may name its moves, and ask for female Pokémon
  where the species allows (Attract only works on the other gender), as a
  player building against a boss would. The check holds named moves to the
  same rule.

| Set | Used for | Level | Team |
|---|---|---|---|
| `falkner` | Falkner | 14 | Chikorita, Geodude, Pachirisu, Sableye, Pidgey (five, so the Mystery Egg fits) |
| `bugsy` | Proton, Bugsy, the rival in Azalea | 19 | Bayleef, Geodude, Onix, Flaaffy, Spearow, Natu |
| `whitney` | Whitney | 24 | Bronzor, Mawile, Heracross, Meditite, Geodude, Kadabra, all female where they can be, moves picked for her team |
| `morty` | the rival in the Burned Tower, Morty | 29 | Houndoom, Mightyena, Raticate, Gyarados, Sableye, Mawile (Dark moves all round) |
| `chuck` | Chuck | 34 | Gardevoir, Xatu, Drifblim, Gyarados, Bronzong, Hypno |
| `jasmine` | Jasmine, then Lake of Rage and the Rocket Hideout | 38 | Magmar, Torkoal, Houndoom, Claydol, Gastrodon, Quagsire |
| `pryce` | Pryce | 42 | Machamp, Heracross, Toxicroak (Low Kick, Poison Jab, Sucker Punch, Dig), Magmar, Luxray, Houndoom |
| `radio_tower` | the Radio Tower takeover: Petrel, the rival in the Underground, Proton, Ariana, Archer | 46 | Alakazam, Bronzong, Claydol, Luxray, Gyarados, Houndoom |
| `elite_four` | from Elm's news on: the Kimono Girls, Ho-Oh, the rival on Victory Road, the Elite Four and Lance | 58 | Ampharos, Gardevoir, Bronzong (Gyro Ball), Jynx (Ice Punch, Psychic, Lovely Kiss, Avalanche), Machamp, Gyarados, each holding an item (see Results); the lead is chosen per room |
| `clair` | Clair | 47 | Luxray, Dewgong, Jynx (Ice Punch, Psychic, Lovely Kiss, Avalanche), Gardevoir, Granbull, Bronzong (Piloswine before Luxray) |

The first Whitney set (Bayleef, Heracross, Meditite, Geodude, Flaaffy,
Gastly) lost both its tries: the hack gives her answers to the usual picks
(Scrappy Miltank hits Ghosts, Intimidate Stantler, Brick Break and Shadow
Claw on Furret). The set above was built against that team; see Results.

The swap doesn't go through the PC's box screens. The bot writes the set
into the party in memory (`pkm.py` reads and writes the game's encrypted
Pokémon data), using one of the player's own Pokémon as the template, so
each new Pokémon carries the player's name and trainer ID and obeys. The old
party is not kept. The swap waits for a moment when the game isn't
rewriting the lead Pokémon, which it does every few frames for the Pokémon
walking behind the player.

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 playtest/story_bot.py /path/to/test/hg-engine/test.nds /path/to/test/hg-engine /path/to/dumped/hg-engine out
```

How it plays:

- **Finding its way:** it plans paths on the maps' collision data, with
  ledges jumped one way only and water left alone, and a route planner picks
  the warps (doors, stairs, ladders, gatehouses, wide doorways and warps in
  front of a doorway) that lead to the next map, across the whole of Johto.
  It reads which map the player is on, and where each person stands, from
  the game's memory. People behind a counter are talked to across it; the
  Pokémon walking behind the player is walked through. Arches (tile
  behaviour `0x2E`) are a walkway over and a path under at right angles, so
  the player leaves one the way it came on. Where the floor changes height
  without the collision data saying so, a step that fails with nobody in the
  way is remembered and the bot goes round. If a scene takes the player to
  another map on the way (Lyra and the Day-Care), it plans again from there.
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
  This happens as the opponent's battler is set up, before the first turn,
  so the game chooses the player's moves, and its replacement when one
  faints, exactly as it does for Falkner. The AI can't answer "Will you
  switch your Pokémon?", so the bot plays with the Set battle style, as a
  player may choose in Options. Should a battle menu still show, the bot
  falls back to the first move and the next healthy Pokémon; `story.json`
  counts the AI's moves and any menus touched. Yes/No questions are answered
  on the touch screen.
- **Losing:** a lost battle (seen by the money it costs) stops the run as
  "lost a battle ... the team whited out".
- **Records:** every battle is added to `out/battles.jsonl`: the trainer,
  where, the team set, won or lost, game time, the AI's moves and every KO
  on both sides with the Pokémon that was out against it. Kept runs are in
  `results/battles.jsonl`.

The story is a list of stages in `story.py`. After each stage the bot saves a
save state (`out/stage_NAME.dst`), so `--from NAME` starts a later run from
there and `--until NAME` stops after it. Key stages check that the story flag
they should set is set (the starter, the Pokégear, the Pokédex, the Sprout
Tower Elder, Falkner's TM, the Mystery Egg, Proton, Bugsy's TM, HM01, the
Radio Card, Whitney's TM, the SquirtBottle, the Sudowoodo, the Burned Tower's
beasts, Morty's TM, HM03, Chuck's TM, the Lighthouse visit, the SecretPotion,
Ampharos cured, Jasmine's TM, Lance at the Lake of Rage, the Hideout's last Electrode, Pryce's TM, each step of the Radio Tower takeover, the Basement Key, the Card Key, Archer, the Ice Path Kimono Girl, Clair, the Dragon Shrine's test). After a lost battle the bot plays the
stage again from its start, as a player would, up to three times (each loss
is still recorded). When the bot gets stuck, or a check fails, it
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

After the gym the carts take the player back out. Then a heal, the rival at
Azalea's west gatehouse, and Ilex Forest: both Farfetch'd, from the forest's
script (the first: step on the twigs south of it, then talk to it from the
north; the second: talk to it from the south so it runs to (49, 54), step on
the twigs east of it, then talk to it from the west), which brings HM01; the
Cut tree (the hack lets the player Cut from the bag with the Hive Badge);
Route 34, where Lyra takes the player into the Day-Care; Goldenrod City; the
Radio Tower quiz (Yes to start, then Yes, Yes, No, Yes, No), without which a
woman stands in Whitney's gym doorway and Whitney is away; and Whitney's
gym: up the west stairs to the raised ring, round it, down the stairs on the
east side and under the arch to her. After she loses, a step onto (13, 11)
starts a girl's scene, and Whitney then hands over the badge and TM45.

Then a heal, the SquirtBottle from the Goldenrod Flower Shop, the Sudowoodo
on Route 36, Route 37 to Ecruteak City, the Morty set at the Pokémon Center
(Bill stands at the counter for a moment there), the Burned Tower (Eusine
and Morty, the rival, and the drop to the basement where the beasts wake:
needed, since a man stands in Morty's gym until then), and Morty's dark gym,
keeping off its trigger areas, which spin the player back to the door.
After a heal: the Rocket Grunt in the Dance Theater, after whom the
gentleman gives HM03 (the hack lets the player Surf from the bag with the
Fog Badge), Routes 38 and 39 to Olivine City, then by water along Routes 40
and 41 to Cianwood City, and Chuck's gym, where the winch at the back has
to stop his waterfall before he will fight.

Then a heal, back across the water to Olivine and up the Lighthouse to
Jasmine. Its 4F stairs from 3F arrive in a part of 4F with no way on: the
player walks out of its east side onto the ledge outside (a way the map's
warps don't list), whose door leads back in to the stairs up. Down again by
the Light Room's elevator. Then the SecretPotion from Cianwood's pharmacy,
up the Lighthouse once more to cure Ampharos, the Jasmine set, and her gym.

Then Route 42 and Mt. Mortar's water to Mahogany Town, Route 43 to the Lake
of Rage, the red Gyarados (talked to until it battles, and caught or
beaten), Lance, and the Rocket Hideout under the souvenir shop with him:
B1F (keeping off the trap floor, whose alarms call out Grunts and wore the
team down to a whiteout in an early run), B2F and B3F, whose maps are split
by walls into parts a warp reaches only from one side (the planner learns a
warp that leads nowhere useful and goes another way), the two Grunts with
the password, the door they open, Petrel, the Murkrow, and on B2F Ariana's
double battle with Lance and the three Electrodes. The bot follows the
Hideout's story variable through those scenes.

Then a heal, the Pryce set, and Pryce's gym. Its floor is ice: the player
slides until something stops it, and some of the ice blocks can be pushed
one tile (found by trying: they are the objects named `_ice`). The bot plans
on the ice with a search over the player's tile and every block's place, so
it pushes blocks where they make a stop, and slides to each trainer and
then to Pryce.

Then the Radio Tower takeover. Leaving Pryce's gym, a call: the Rockets have
taken the tower. Back west to Goldenrod and the Radio Tower set; in the
Goldenrod Underground a Rocket hands over a uniform; in it, the Grunt on the
tower's 1F stairs, talked to, steps aside, and the rival appears; up to 5F,
where the "Director" is Petrel, who battles and gives the Basement Key. Then
the Underground's locked door, the switch room behind it (the rival battles),
and the warehouse, where the real Director gives the Card Key. The switch room
has three switches that each flip their own set of shutters, and an emergency
switch by the warehouse door; the shutters reset whenever the player comes in.
The bot tries each choice of switches from a save state until the way is open,
going in and coming back out. Then the Card Key in the 3F slot, Proton on 4F,
Ariana on 5F, and the elevator at the top of 5F, which rides by itself to the
Observation Deck (its door leads wherever it went, a warp the planner can't
follow), where Archer battles. The bot heals at the Pokémon Center before each
of the three Executives, as a player with potions would.

Then back east to the Ice Path along Route 44. On 1F, HM07 first (an item
ball on the ice: until it is picked up, a man by the stairs down turns the
player back). On B1F, four Strength boulders and four holes: each boulder
pushed into a hole lands on B2F's ice as something to stop against.
`boulders.py` plans the pushes (one boulder at a time, each into a hole near
it, with a full search over all of them to fall back on); the bot uses
Strength from the bag on the first push, checks the game after every move and
plans again whenever it differs (a wild Pokémon, a push that leaves the player
elsewhere). The bot now plans slides on every icy map. Across B2F to B3F and
back up the east side to 1F, where a Kimono Girl stands on the last slope:
talked to from above, she asks if the player is in a hurry, and Yes sends her
off. Then Blackthorn City.

Clair's gym is islands in lava joined by three platforms that slide or rotate
when the player steps on one of their buttons (`src/field/gymmick/blackthorn.c`
in the decompilation); three tiles spin the player back to the door. The bot
reads the platforms' floors and buttons from the game's memory (lava is
otherwise not walkable), and searches from save states over which buttons to
step on, trying first the layouts that let it walk furthest north. It walks
to the tile beside a button and takes the last step itself (the platform
moves off with the player), keeps off every other button on the way, and
steps off and back on to press one it stands on. The search found a way
across in 23 presses; `CLAIR_ROUTE` in `story.py` keeps them, so later runs
just step on them, and search only if that stops working.

Clair holds back the badge until the player passes the Dragon Shrine's test.
The platforms are left where they took the player to her, which is no way
back, so the bot leaves by the spin trap on her island (it sends the player to
the door). The Dragon's Den is reached by water behind the gym; its lower
lake, where the shrine stands, is below a whirlpool, which the bot crosses
with Whirlpool from the bag (HM05, from Lance in the Rocket Hideout): it
plans across whirlpool tiles as water, and facing one presses A and answers
Yes, as for Surf. The shrine door is entered from the south. Walking in starts
the elder's five questions, whose three answers each are on the touch screen;
the script marks the wrong ones, so the right ones are the 1st, 1st, 2nd, 1st
and 2nd. Touches on those buttons don't always take, so the bot waits for
them to show, moves the cursor down to the answer with the keypad and presses
A, and counts it only once the buttons have gone. Then Clair hands over the
Rising Badge.

Then the way to the League, which HeartGold holds back twice. At New Bark's
east edge Mom turns the player back until they have seen Elm, and then Lyra
does until they have met Ho-Oh. So: Routes 45 and 46 (some of Route 45's
ledges carry the blocked bit, and are jumped all the same) to Elm; back to
Ecruteak, where the rival appears and the five Kimono Girls are called to the
Dance Theater, and their five battles one after another (the scene pauses
between them, so the bot keeps on until the Clear Bell is given); the monk in
the Bell Tower's barrier station, who steps aside when talked to; up the
tower to the roof, where the long cutscene of the dance brings Ho-Oh down
(Lv. 52 in the hack), a battle that has to be won. Then east over Route 27 and
up Tohjo Falls (the bot now uses Waterfall from the bag, as it uses
Whirlpool), Route 26 and the League gate to Victory Road.

Victory Road is three floors of Strength boulders, stairs that lead to parts
of a floor with no way on, and holes on 3F that drop to parts of 2F its stairs
don't reach. The holes are in a script, not the warp lists, so the route planner
was given them (`HOLES` in `story_bot.py`). The boulder planner now also pushes
boulders out of the way, not only into holes, and leaves the walking between
pushes to the bot's walk, which knows bridges. Where the planner finds no way,
the stage tries each set of stairs up and each hole from a save state until
one leads on: up to the 2F stairs at (51, 39), down 3F's hole at (55, 42), the
boulder at (50, 28), up again at (56, 22), down the hole at (26, 38), and up the
stairs at (27, 44) to the exit. The rival waits on 3F.

At the League: the nurse, the Elite Four set from the PC there, the guard at
the counter, and one stage for each room and for Lance. There is nowhere to
heal between the rooms, so (as for Clair, and the rival on Victory Road after
the whole cave) the harness heals the party where it stands before each, HP,
status and PP, and gives back berries used up, as a player carrying potions
and spare berries would. With that, each room starts the same however the one
before went, so a loss is retried from that room (in the game it sends the
player back to Will). A retry starts from the same save state, so the bot waits
a random while first; otherwise the battle plays out move for move the same.
Beating Lance takes the player to the Hall of Fame part way through the walk up
to him, which the stage allows for. The Hall of Fame scene draws much like a
battle screen, so the bot only presses A through it and the credits (once it
took the scene for a battle and called it a whiteout) and ends back in the
player's bedroom, saved as `stage_champion.dst`: the end of the story.

Each room has its own lead (`LEADS` in `story.py`), as a player would reorder
the party at the heal: Gyarados for Will, Bronzong for Koga, Gardevoir for
Bruno, Ampharos then Machamp for Karen, Ampharos for Lance.

**A heal before every boss.** Every Gym Leader and Rocket executive the bot
talks into a battle, from Falkner on, now starts with the party healed where
the player stands beside them (`talk(..., boss=NAME)`). Without it the bot
kept meeting bosses worn down by their gyms' trainers, which a player would
have patched up with potions. Lt. Surge was the clearest case: his gym's
trainers took three of the team every time, and he won four tries running.
Results recorded before this change (all of `results/battles.jsonl` up to
the `rebalance-0022` runs) had heals only before Clair, the Victory Road
rival and the League. Fights that start from a scene, such as the rival and
Ariana's double battle in the Hideout, are not covered.

`grind_test.py` grinds in one area with the harness's party at a set level and
logs each battle's experience against `level_curve.py`'s formula; it sends
in the next Pokémon after a faint and passes over moves with no PP left
(`LEVEL_CURVE.md`, "A grind measured in the game").

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 playtest/grind_test.py /path/to/test/hg-engine/test.nds /path/to/test/hg-engine /path/to/dumped/hg-engine out R27 50 30
```

`save_carry.py` checks that a save from the last release carries on in a new
one: it continues the game from that save, wins two wild battles and saves
again.

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 playtest/save_carry.py /path/to/new/release.nds /path/to/last/release.dsv out
```

The old save is copied, never written, so the same one can be checked again;
`out/next.dsv` is the new release's save, for the release after. Each battle
uses the first move that still has PP.

`rematch_test.py` fights any trainer with a team set, played by the story bot (with smart turns when
`STORY_SMART=1`): the harness starts the battle from the bedroom PC after the bot writes the set over the
party. It is how the Gym Leader rematches are played, which the story bot has no stages for.

```bash
STORY_SMART=1 SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 playtest/rematch_test.py /path/to/test.nds /path/to/hack/hg-engine /path/to/original/hg-engine out elite_four_2 80 5 712
```

`shop_test.py` shows what the Goldenrod Department Store's 4F clerk sells at
each badge count (by default 2, 4, 6 and 7, the evolution items' tiers): it
puts the player at the counter with that many badges, opens Buy and saves
every page of the list side by side in `out/list_<badges>.png`.

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 playtest/shop_test.py /path/to/test.nds /path/to/hack/hg-engine /path/to/original/hg-engine out
```

`challenge_test.py` checks the challenge rules: that the woman in the player's house turns the level
cap on and off again; that with no badges a Lv. 14 party leader gains no experience from a wild battle
on Route 29 with the cap on, and some with it off; that with no items on, a Potion from the bag in a
trainer battle doesn't get as far as choosing a Pokémon, though it does with the rule off; and that with
the shared experience on, the second Pokémon gets about half what the lead does from a wild battle, and
nothing with it off; and the same over a whole trainer battle with two foes.

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 playtest/challenge_test.py /path/to/test.nds /path/to/hack/hg-engine /path/to/original/hg-engine out
```

`hm_test.py` tries each field move from the bag (Rock Smash, Cut, Strength, Surf, Whirlpool, Waterfall and
Rock Climb), with a party that knows only Tackle: with the HM and its badge it must ask to use it and then
work (the rock or tree goes, the boulder moves, the player gets on, through or up); one badge short of it,
or without the HM, it must not ask. It finds a place for each in the map data, and names after `out` limit
it to some moves (such as `Surf Rock_Climb`).

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 playtest/hm_test.py /path/to/test.nds /path/to/hack/hg-engine /path/to/original/hg-engine out
```

`champion_test.py` checks the post-game unlocks that wait for the Champion (FLAG_GAME_CLEAR), with the flag
clear and set: Cliff Cave's Rock Smash rocks (moved aside before); the Bug-Catching Contest's own check, read
as it runs when the player enters the contest at the Route 36 gate; the Pokéathlon Dome prize clerk's two
checks; and the Friendship Room scene that shows the Supreme Cup's receptionist. The contest is only held on
Tuesdays, Thursdays and Saturdays, and the emulator keeps the computer's date, so on other days that check is
skipped. It also checks the Pokégear radio's Pokémon Music preset (registering the Radio Card in the save in
memory first), and Raikou and Entei waiting in the Burned Tower B1F (`beasts`). Names after `out` (such as
`pokeathlon`) run only those.

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 playtest/champion_test.py /path/to/test.nds /path/to/hack/hg-engine /path/to/original/hg-engine out
```

`qol_test.py` plays the free Move Reminders (Cherrygrove's and Blackthorn's, with no Heart Scale), the hyper
trainer on Goldenrod 5F (a Bottle Cap on Speed, Speed again once it is 31, a Gold Bottle Cap on every stat), an
Adamant Mint used from the bag, a King's Rock evolving a Slowpoke, a Rare Candy
evolving a Lv. 36 Kadabra, Voltorb among 60 wild Pokemon on Route 38, and Scyther and Pinsir among 120 in
the National Park. Names after `out` (such as
`hyper_all mint`) run only those.

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 playtest/qol_test.py /path/to/test.nds /path/to/hack/hg-engine /path/to/original/hg-engine out
```

`breed_test.py` leaves a Ditto and a Magikarp at the Route 34 Day Care, walks inside it until the game makes
an egg (it must within 256 steps), has the Day-Care Man hand it over, and walks until it hatches (within 1,100
steps; a Magikarp egg can't hatch before step 1,276 in the original game). It prints its steps as it goes.

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 playtest/breed_test.py /path/to/test.nds /path/to/hack/hg-engine /path/to/original/hg-engine out
```

`walk_test.py`'s `features` test buys through the restocked counters; `WALK_COUNTERS` (comma-separated parts
of their names, such as `TM counter,berry stand`) limits it to some of them.

Settings, all environment variables: `STORY_RETRIES` (tries per stage before
it stops, default 3), `STORY_REFILL_BERRIES` (`0` stops the berry refill
between rooms), `STORY_TEAM_<SET>` (swap in another set where that one is
due, such as `STORY_TEAM_CLAIR=clair_first`) and `STORY_JITTER` (up to this
many frames of random waiting after a stage's save loads, default 0; without
it, two runs from the same save play every battle out the same way),
`STORY_BOSS_HEAL` (`0` turns off the heal before each boss),
`STORY_LEVEL_<SET>` (play a set at another level, devolved and with the
moves it could know then, as a player would have it; see `LEVEL_CURVE.md`)
and `STORY_SMART` (`1` has the bot play its own turns: it switches to a
better matchup, uses potions at 40% HP, and picks who comes in after a
faint, by `smart.py`; `STORY_SMART_POTIONS` sets how many potions it carries,
default 6). `STORY_BATTLE_ITEMS` puts items in the player's trainer item
slots for the game's AI, which in practice never uses them (`BALANCE.md`).

The bot surfs once it has HM03: water counts as walkable, and a step from
land onto water is Surf (face it, A, Yes). It heals after every gym, and
after the Azalea rival.

# Results

The boss results, brought together with ways to fix the hard fights, are in
[BALANCE.md](BALANCE.md) (`python3 balance.py` rebuilds its table).

What level a player's team reaches by each boss without grinding, worked out
from the game's data with `level_curve.py`, is in [LEVEL_CURVE.md](LEVEL_CURVE.md).

**Save states and code changes.** A save state holds the game's code as it
was loaded in memory. After a patch that changes data only (trainer teams,
say), saves from an earlier build still work. After one that changes code
(such as patch 0025, double experience), they freeze at the next battle:
start again from a fresh boot (no `--from`), which makes a new
`bedroom.dst` with the new build.


From `results/battles.jsonl`.

**Bugsy**, with the Lv. 16 reference team before the boss sets: two wins in
five runs. With the `bugsy` set: two wins in two.

**Whitney**, with the `whitney` set: six wins in ten runs. Our Pokémon
fainted 2, 5, 2 and 4 times in the four wins with KO records, 5 and 6 times
in the two losses. KOs scored by her team, over those six battles (credited
to the Pokémon of hers that was out when ours fainted):

| Her Pokémon | KOs | Whose |
|---|---|---|
| Dunsparce (Serene Grace: Rock Slide, Glare, Shock Wave, Water Pulse) | 8 | Geodude 4, Mawile 3, Meditite 1 |
| Stantler (Intimidate, Hypnosis) | 6 | Heracross 4, Meditite 2 |
| Miltank (Scrappy, Rollout, Attract) | 6 | Heracross 2, Kadabra 2, Mawile 1, Meditite 1 |
| Furret | 4 | Bronzor 4 |

Dunsparce is the one to look at; Serene Grace doubles Rock Slide's flinch and
Glare's paralysis.

**Morty**, with the `morty` set: won the one run, with five of our six
fainted (Drifblim took three). The same set beat the Burned Tower's rival
in two runs, losing three and none.

**Chuck**, with the `chuck` set: won the one run, with four fainted
(Poliwrath, Heracross twice, Machoke).

**Jasmine**, with the `jasmine` set: won the one run, with three fainted
(Magmar to Steelix, Torkoal to Magneton, Gastrodon to Scizor).

**Lake of Rage and the Hideout**, still on the `jasmine` set: 67 battles,
59 won. Petrel won with five of ours fainted. Ariana and her Grunt, with
Lance's Dragonite beside us, beat us four times in a row: those were runs
where the B1F traps had already worn the team down and the bot had not
healed, so one KO on Houndoom ended each; the bot now heals at the Hideout's
end, and the next two tries won. Four "lost" wild battles on B1F are the same
thing (Houndoom last standing, a wild Geodude). With a healed team the
Hideout is fine.

**Pryce**, with the `pryce` set: one win in three tries (37.5 game minutes
for the stage). Each try met Patton and Jill on the ice first, and won both.
KOs scored by his team (credited as above):

| His Pokémon | Try 1 (lost) | Try 2 (lost) | Try 3 (won) |
|---|---|---|---|
| Jynx (Ice Beam, Psychic, Energy Ball, Lovely Kiss; Wise Glasses) | 6: the whole team | 1 (Machamp) | 2 (Machamp, Magmar) |
| Dewgong | – | 2 (Magmar, Luxray) | 1 (Houndoom) |
| Mamoswine | – | 3 (Heracross, Houndoom, Toxicroak) | 1 (Luxray) |
| Lapras | – | – | 1 (Heracross) |
| Delibird, Sneasel | – | – | – |

Jynx is the one to look at: it opened all three battles after Delibird and
took nine of the seventeen KOs, sweeping the whole team once. Lovely Kiss
puts a Pokémon to sleep, and with Wise Glasses Ice Beam and Psychic between
them hit most of a team that has to bring Fighting types for the rest of
his. Sucker Punch on Toxicroak and Houndoom's Dark moves are the set's
answers, but they rarely got to act before Jynx did.

**The Radio Tower**, with the `radio_tower` set: 36 battles, 30 won. The
Grunts, the scientists and Petrel (six Poison types) fell to Alakazam or
Bronzong alone, none of ours fainting. The rival in the Underground won with
two fainted.

| Boss | Result | Ours fainted | KOs by their Pokémon |
|---|---|---|---|
| Proton | 4 wins in 4 | 3, 4, 3, 4 | Houndoom 5 (Alakazam 4), Weezing 4 (Gyarados 3), Muk 3, Qwilfish 2 |
| Ariana, healed first | 1 win in 2 | 6, then 2 | **Honchkrow 6** (the whole team in the loss), Ariados 1, Crobat 1 |
| Archer | 2 wins in 4 | 3, 6, 6, 2 | Crobat 5 (always last, finishing Claydol and Luxray), Houndoom 4 (all Bronzong), Sneasel 4, Persian 2, Weezing 2 |

Three more losses to Ariana came straight after Proton, before the bot healed
between them; Honchkrow took five of those KOs too. Honchkrow (Lv. 45, Super
Luck with a Scope Lens: Foul Play, Brave Bird, Psychic, Roost) is the one to
look at, as Jynx is for Pryce: its critical hits get through even the
Electric type brought for it. Archer is a fair fight for this set.

**The Ice Path** needed no battles worth noting (wild Pokémon only).

**Clair**, with the `clair` set: no wins in nine. Her gym's five Ace Trainers
(Dratini, Horsea, Seadra, Dragonair) have to be fought on the way to her, and
there is nowhere to heal inside. With Piloswine in the set (five tries) it
fainted to a Seadra every time before reaching her, and Dewgong took on most
of the trainers alone; with Luxray instead (four tries) Luxray or Dewgong
fell to them as often. She still had 1 to 4 of her six left at the end of
each loss. KOs on our Pokémon in the nine battles with her:

| Her Pokémon | KOs |
|---|---|
| Gyarados (Intimidate, Dragon Dance; Aqua Tail, Earthquake, Crunch; Wacan Berry) | **15** |
| Gabite | 8 |
| Dragonair | 7 |
| Flygon | 6 |
| Kingdra | 5 |
| Altaria | 3 |

Gyarados is the one to look at: once it has a Dragon Dance in, it sweeps what
is left. The bot can't use potions (it heals only at Pokémon Centers), so a
gym that has to be crossed before its leader is harder for it than for a
player.

So the harness now heals the party where it stands in front of Clair, after
her trainers (`restore_party` in `story_bot.py`, test harness only), in place
of the potions a player would use. With that, both sets beat her on the first
try: the `clair` set with three of ours fainted (Granbull finished Kingdra and
Gyarados), and the first set (`clair_first`, Piloswine for Luxray, run with
`STORY_TEAM_CLAIR=clair_first`) with four. Clair herself is a fair fight; what
made her a wall for the bot was her gym's trainers, fought without healing.

**From Elm's news to Lance**, with the `elite_four` set: the five Kimono Girls
won at the first try each (one Pokémon each, an Eeveelution), and Ho-Oh beaten
by Gardevoir alone. The rival on Victory Road won two battles against a team
the cave had worn down; healed first, the bot beat him with three of ours
fainted.

The Elite Four set changed as the data came in. A player's single team has to
cover five type specialists, and the bot's battle AI never switches out at a
disadvantage (a Swords Dance or Dragon Dance user that gets going sweeps):

1. Gardevoir, Houndoom, Jynx, Luxray, Golem, Heracross, holding Oran Berries.
   Koga beat it three times out of four.
2. Bronzong for Houndoom (Poison moves can't touch it), still without held
   items: Koga's Ariados (Focus Sash, Swords Dance) swept three.
3. Held items a player has by now: Sitrus and Lum Berries and the type-resist
   berries from the Goldenrod Department Store, and the NeverMeltIce from the
   Ice Path. Koga fell (Bronzong knocked out five of his six), but Karen won
   every battle: Honchkrow, Gengar (Levitate, Hypnosis) and Weavile (Focus
   Sash, Swords Dance).
4. Machamp for Golem, a second Fighting type: Karen beaten at last, then
   Lance's Charizard swept four of ours in three of four battles.
5. Gyarados (Wacan Berry) for Heracross, for Charizard: the four Elite Four
   beaten at the first try each, and Lance once.
6. Ampharos (Shuca Berry) for Luxray, and a lead chosen for each room. Will,
   Koga and Bruno fell within two tries each. Karen won 14 times with
   Ampharos alone in front (her Tyranitar knocked out 49 of ours over those
   battles, Gengar 16); with Ampharos then Machamp she fell at the first try.
   Lance was beaten 5 times out of 8, Gardevoir finishing his Dragonites and
   Kingdra each time, and the run went on through the Hall of Fame and the
   credits.

Over the first five versions:

| Boss | Won |
|---|---|
| Will | 14 of 18 |
| Koga | 6 of 11 |
| Bruno | 5 of 6 |
| Karen | 2 of 11 |
| Lance | 1 of 22 |

With the sixth version (run `ampharos-league` in `results/battles.jsonl`):
Will 1 of 1, Koga 1 of 2, Bruno 1 of 2, Karen 1 of 15, Lance 5 of 8. In
Lance's battles Aerodactyl knocked out 12 of ours, Gyarados 8, Charizard and
Kingdra 6 each, Dragonite 4.

Lance is the one to look at. His Gyarados (Intimidate, Dragon Dance, Wacan
Berry) leads, and before the sixth version in most battles has swept three or four of ours before
anything else of his has to move; Aerodactyl, Charizard and the two
Dragonites finish the rest. KOs on our Pokémon over the 22 battles: Gyarados
41, Aerodactyl 29, Charizard 28, Dragonite 22, Kingdra 11. Koga's Ariados and
Karen's Tyranitar, Gengar and Weavile are next.

Two bugs found on the way, both fixed: the in-place heal could read the
Pokémon walking behind the player while the game had it decrypted, and write
the garbage back (the battles fought before the fix, up to the fifth version's
first run, may have had a damaged Pokémon in them); and the KO records missed a
Pokémon sent out and knocked out between two of the bot's looks at the battle.

**The clean run** from the bedroom to Whitney, with every stage in order:
83 battles, 78 won. The losses: the Azalea rival twice and Whitney once
(each won on a retry), a policeman on Route 34 before the bot healed after
the rival, and one false loss in Lyra's catching lesson from before the
money check was fixed.
