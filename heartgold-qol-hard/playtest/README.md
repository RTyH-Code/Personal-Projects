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
Ampharos cured, Jasmine's TM, Lance at the Lake of Rage, the Hideout's last Electrode, Pryce's TM). After a lost battle the bot plays the
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

The bot surfs once it has HM03: water counts as walkable, and a step from
land onto water is Surf (face it, A, Yes). It heals after every gym, and
after the Azalea rival.

# Results

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

**The clean run** from the bedroom to Whitney, with every stage in order:
83 battles, 78 won. The losses: the Azalea rival twice and Whitney once
(each won on a retry), a policeman on Route 34 before the bot healed after
the rival, and one false loss in Lyra's catching lesson from before the
money check was fixed.
