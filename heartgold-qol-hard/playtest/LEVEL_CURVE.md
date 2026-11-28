# The level curve

What level does a player's team reach by each boss without grinding? The story bot can't answer that, since
it swaps in a team at the boss's top level before each fight. `level_curve.py` works it out from the game's
data instead:
- **The trainers:** it splits the story into stretches, one per boss, with the maps a player passes through
  on the way. Every trainer on those maps is beaten once, in order, and each boss's own team counts towards
  the next stretch.
- **The formula:** experience follows the hack's scaled formula, which gives more for beating higher-level
  Pokémon and less for lower ones. Trainers' Pokémon give half as much again, and since patch 0025 every
  battle gives double.
- **Checked against the game, before patch 0025:** a Violet Gym trainer's Spearow gave exactly the predicted
  99 experience, and Falkner's team gave 1,042 against a predicted 1,054.
- **Checked again with patch 0025,** in a run from a fresh boot: the same Spearow gave 198, and Falkner's team
  2,064.

```bash
python level_curve.py /path/to/hack/hg-engine /path/to/original/hg-engine
```

It models two ways to share the experience out:
- **Even team:** six Pokémon from the start, each KO going to the lowest of them, as a player who rotates
  the team.
- **One carry:** a single Pokémon takes every KO, the upper bound for a player's strongest.

Each is shown for the two common growth rates: medium fast, and medium slow, which the starters use. The
last two columns count the wild Pokémon (from the stretch's grass, at its odds) the even team would also
need to beat to have all six at the boss's average level on arrival.

## With double experience (patch 0025)

| Boss | Their levels | Trainers on the way | Even team, medium fast | Even team, medium slow | One carry, medium fast | One carry, medium slow | Wild KOs to reach their average, medium fast | The same, medium slow |
|---|---|---|---|---|---|---|---|---|
| Falkner | 11-14 (avg 12) | 12 | 8 | 9-10 | 12 | 14 | 46 | 21 |
| Proton, Slowpoke Well | 15-18 (avg 16) | 17 | 13-14 | 14-16 | 20 | 21 | 23 | 4 |
| Bugsy | 16-19 (avg 18) | 4 | 14-16 | 16-18 | 23 | 24 | 21 | 11 |
| Rival, Azalea | 18-21 (avg 19) | 0 | 15-16 | 17-18 | 24 | 25 | 14 | 8 |
| Whitney | 21-24 (avg 22) | 14 | 18-19 | 20-21 | 29 | 30 | 22 | 10 |
| Rival, Burned Tower | 24-27 (avg 25) | 21 | 23 | 25 | 36 | 37 | 0 | 0 |
| Morty | 26-29 (avg 28) | 4 | 25 | 26-27 | 39 | 40 | 27 | 10 |
| Chuck | 31-34 (avg 32) | 36 | 31-32 | 32-33 | 47 | 48 | 0 | 0 |
| Jasmine | 35-38 (avg 36) | 0 | 32-33 | 33-34 | 49 | 49 | 58 | 46 |
| Petrel, Rocket HQ | 36-39 (avg 37) | 20 | 35 | 36 | 53 | 54 | 0 | 0 |
| Ariana, Rocket HQ | 37-40 (avg 38) | 4 | 36 | 37 | 55 | 55 | 0 | 0 |
| Pryce | 38-42 (avg 40) | 5 | 37-38 | 38 | 57 | 57 | 5 | 2 |
| Proton, Radio Tower | 41-43 (avg 42) | 11 | 39-40 | 40-41 | 60 | 60 | 2 | 1 |
| Petrel, Radio Tower | 43-44 (avg 43) | 1 | 41-42 | 42-43 | 63 | 63 | 0 | 0 |
| Rival, Goldenrod Tunnel | 41-44 (avg 42) | 6 | 42 | 43 | 64 | 64 | 0 | 0 |
| Ariana, Radio Tower | 43-45 (avg 44) | 3 | 43-44 | 44 | 66 | 66 | 0 | 0 |
| Archer, Radio Tower | 43-46 (avg 44) | 0 | 44 | 44-45 | 67 | 67 | 0 | 0 |
| Clair | 44-47 (avg 45) | 12 | 45-46 | 46-47 | 70 | 69 | 0 | 0 |
| Rival, Victory Road | 48-50 (avg 49) | 25 | 49 | 49-50 | 74 | 74 | 0 | 0 |
| Will | 49-51 (avg 50) | 0 | 50 | 50-51 | 76 | 75 | 0 | 0 |
| Koga | 50-52 (avg 51) | 0 | 50-51 | 51 | 77 | 76 | 0 | 0 |
| Bruno | 51-53 (avg 52) | 0 | 51-52 | 51-52 | 78 | 77 | 0 | 0 |
| Karen | 53-55 (avg 54) | 0 | 52-53 | 52-53 | 79 | 78 | 20 | 20 |
| Lance | 55-58 (avg 56) | 0 | 53 | 53-54 | 80 | 79 | 41 | 43 |

Wild KOs in all to the first Hall of Fame: 279 (medium fast), 176 (medium slow).

**An even team of six stays within about 3 levels under each boss's average all the way.** It falls furthest
behind early on, 3 to 4 levels at Falkner, and by the League it is 2 to 3 under. Wild battles met on the way
make up most of that. Having all six right at every boss's average takes about 180 to 280 wild KOs over the
whole game. No stretch needs more than about 60: the most are before Jasmine, Falkner and Lance.

Until patch 0027 it was about 630 to 1,040. The grass and caves on Johto's main path kept HeartGold's own
levels, Lv. 2-5 before Falkner and 14-19 before Pryce, so before Falkner it took about 180 wild KOs, before
Bugsy about 120 and before Jasmine about 160. Patch 0027 puts each of those areas a little under the boss
after it (55-80% of his average before Falkner, 75-85% after).

Checked in the game with `walk_test.py` on the build with the test harness: on 17 of the 20 areas tried, every
wild Pokémon met matched the new tables (Route 30 Spinarak 7 and Rattata 9, Route 32 Wooper and Mareep 13,
Ilex Forest Oddish 16, Route 34 Glameow 19, Route 37 Stantler 24, Route 39 Raticate 29, Mt. Mortar Makuhita
32, Route 44 Munchlax 37, the Ice Path Swinub 34-35, and so on). Route 42 matched for the two met before a
trainer stepped in; on Route 43 and in the National Park a trainer or the park's scene took over first.

Fishing, Rock Smash and Headbutt (patch 0032) were checked the same way. Headbutt on 20 Johto maps: every
Pokémon at the new levels (Route 30 Hoothoot 16-17, Route 43 Hoothoot 33, Route 26 Pineco 45 and Spinarak
49; Route 38's one exception was Lass Dana's Flaaffy, a trainer who walked up). Fishing on 10: the Good Rod
at the new levels everywhere (Route 30 Magikarp 28, Olivine Krabby 27, Lake of Rage 32, Route 44 Poliwag
36-37, Route 26 Tentacool 48-49), the Old Rod at 10 and the Super Rod at 40 as before. Rock Smash: the Ruins
of Alph (Geodude 24), Dark Cave (Dunsparce 22), Cianwood (Krabby 26, Shuckle 29) and Cliff Cave (Krabby 26,
Kingler 29). Cliff Cave's map script moves its rocks aside until the Champion is beaten (`FLAG_GAME_CLEAR`,
the post-game gate patch 0002 sets up), so its Rock Smash Pokémon are post-game; the test sets the flag.
Patch 0035 puts them back at their levels before patch 0032 (Krabby 23-30, Kingler 32-36), checked in the
game the same way: Krabby 26, Kingler 36.

The Super Rod (patch 0037) was checked the same way on six Johto maps: every Pokémon at the new Lv. 62
(Route 30 Poliwag, Olivine Staryu, Lake of Rage Gyarados, Dragon's Den Dratini, Route 44 Remoraid, Route 26
Lanturn).

Patch 0029 puts the water in the same bands, from where a player can first surf. `walk_test.py`'s surf check on
the build with the test harness met only Pokémon in the new tables on seven of ten areas: Route 34 Tentacool
27-29, Route 41 Tentacruel 29, Route 42 Goldeen and Seaking 32, Route 43 Magikarp 32-33, the Lake of Rage
Magikarp 31-32 and Gyarados 31, Route 44 Poliwag 37-38, Route 45 Magikarp 37-41. In New Bark Town nothing appeared
in 750 steps, on Route 40 a Swimmer stepped in, and at Blackthorn the test couldn't start surfing from the bank it
tried. Run as one batch the check stopped without an error after loading; one area at a time, each ran through.

Patch 0030 brings Routes 47 and 48 and Cliff Cave into Chuck's band, as they open off Cianwood. Checked the same
way: Route 48 Growlithe 28, Hoppip and Girafarig 27; Cliff Cave Machoke 28, Onix 27, Wooper 26; Route 47's water
Seel 27, Staryu 27-28.

## The post-game

The same model carried on into Kanto, in the order the story bot plays it (from Vermilion off the S.S.
Aqua), with the second round and Red after the eight Kanto badges:

| Boss | Their levels | Trainers on the way | Even team, medium fast | Even team, medium slow | One carry, medium fast | One carry, medium slow | Wild KOs to reach their average, medium fast | The same, medium slow |
|---|---|---|---|---|---|---|---|---|
| Lt. Surge | 61-64 (avg 62) | 10 | 56-57 | 56-57 | 85 | 84 | 72 | 78 |
| Sabrina | 63-66 (avg 64) | 11 | 59-60 | 59-60 | 90 | 89 | 0 | 0 |
| Erika | 63-66 (avg 64) | 4 | 61 | 61 | 93 | 91 | 0 | 0 |
| Misty | 65-68 (avg 66) | 18 | 64-65 | 64 | 98 | 96 | 0 | 0 |
| Janine | 65-68 (avg 66) | 34 | 68 | 67-68 | 100 | 100 | 0 | 0 |
| Brock | 67-70 (avg 68) | 14 | 70 | 69-70 | 100 | 100 | 0 | 0 |
| Blaine | 69-72 (avg 70) | 3 | 71 | 70 | 100 | 100 | 0 | 0 |
| Blue | 73-76 (avg 74) | 8 | 72 | 72 | 100 | 100 | 0 | 0 |
| Will, second round | 77-80 (avg 78) | 0 | 73 | 72-73 | 100 | 100 | 61 | 85 |
| Koga, second round | 78-81 (avg 79) | 0 | 73-74 | 73 | 100 | 100 | 16 | 16 |
| Bruno, second round | 79-82 (avg 80) | 0 | 74-75 | 73-74 | 100 | 100 | 15 | 19 |
| Karen, second round | 81-84 (avg 82) | 0 | 74-75 | 74 | 100 | 100 | 51 | 55 |
| Lance, second round | 85-88 (avg 86) | 0 | 75-76 | 74-75 | 100 | 100 | 133 | 146 |
| Red | 92-95 (avg 93) | 0 | 76-77 | 75-76 | 100 | 100 | 304 | 335 |

Wild KOs in all in the post-game: 652 (medium fast), 734 (medium slow), with the second round's grind on
Mt. Silver.

**Kanto's gyms are paced by their trainers.** A team arriving from the League at 53 is six under Lt. Surge;
about 75 wild battles on Routes 6 and 11 make that up, and from there Kanto's trainers alone keep it at or
above each leader's average, Blue included.

**The second round and Red are a long grind, and stay one.** No trainers stand between Blue and the
Indigo Plateau, so the team arrives at the second round at about 73, five under Will and thirteen under
Lance (85-88). Getting there takes about 280 wild battles, and Red (92-95) about 300 more. Mt. Silver
(Lv. 62-70) is the quickest place for it, and the grass a player passes on the way (Viridian, Route 22,
Lv. 46-48) takes half as long again. Raising Mt. Silver's levels wouldn't change much: the hack's scaled
formula gives less for a wild Pokémon well under the team, but not much more for one nearer it, so 12
levels more would cut the grind by only about 30%. These are the game's peak fights, and they stay as they
are.

## A grind measured in the game

`grind_test.py` grinds in one area on the build with the test harness, as a player would: the first move with
PP left, the next Pokémon in after a faint, moves to learn turned down, a heal between battles. Thirty battles
on Route 27 with the harness's party at Lv. 50 (its lead a Typhlosion, medium slow), against the area's Lv.
48-49 Pokémon since patch 0026:

- **All 30 won.** Three had a faint, and the test sent in the next Pokémon each time.
- **The formula holds.** In 26 of the 27 battles the lead fought alone, the experience it gained was exactly
  `level_curve.py`'s figure for its level. The other one matched the figure for the level before, so the read
  lagged a level-up. Over all 30, the party gained 87,936 against 87,422 predicted.
- **The model is a little quick.** The lead reached Lv. 55 on the 18th battle and 58 on the 29th; for one
  Pokémon on Route 27's daytime odds, the model says the 15th and the 26th. The game met as many Raticate as
  Dodrio (12 each) and fewer of the Rapidash that give more, and the three battles with a faint shared their
  experience. So the wild-battle counts above may run 10-20% short of what a player needs.

The League's share was larger until patch 0026. The grass on Routes 26 and 27 and in Victory Road was Lv. 23
to 41, far enough under a team at 50 that the scaled formula gave little for it: about 160 wild KOs to bring
the team to Lance's average, and about 490 to the Lv. 55 the story bot needed to get past Will. With those
areas at Lv. 45-50 it is about 45 to Lance's average and about 145 to 55.

The story bot's test teams (`team_sets.py`) were set at each boss's top level. A player who doesn't grind
arrives a few levels below that. `BALANCE.md` has the bosses played again at these levels.

## Before patch 0025, and with a modern Exp. Share instead

| Boss | Their average | Before patch 0025, medium fast | Before patch 0025, medium slow | Modern Exp. Share instead, medium fast | Modern Exp. Share instead, medium slow |
|---|---|---|---|---|---|
| Falkner | 12 | 6-7 | 8 | 9 | 10-11 |
| Proton, Slowpoke Well | 16 | 10-11 | 12-13 | 15 | 16 |
| Bugsy | 18 | 12-13 | 14-15 | 17 | 18-19 |
| Rival, Azalea | 19 | 12-13 | 14-15 | 18 | 19-20 |
| Whitney | 22 | 15-16 | 17-18 | 21 | 23 |
| Rival, Burned Tower | 25 | 19-20 | 21 | 26-27 | 28 |
| Morty | 28 | 21 | 23 | 29 | 30 |
| Chuck | 32 | 26 | 27-28 | 35 | 36 |
| Jasmine | 36 | 26-28 | 28-29 | 36-37 | 37-38 |
| Petrel, Rocket HQ | 37 | 29-30 | 31 | 40 | 41 |
| Ariana, Rocket HQ | 38 | 30 | 31-32 | 41 | 42 |
| Pryce | 40 | 31-32 | 32-33 | 42 | 43 |
| Proton, Radio Tower | 42 | 33-34 | 34-35 | 45 | 46 |
| Petrel, Radio Tower | 43 | 34-35 | 35-36 | 47 | 47-48 |
| Rival, Goldenrod Tunnel | 42 | 35-36 | 37 | 48 | 49 |
| Ariana, Radio Tower | 44 | 36-37 | 37-38 | 49 | 50 |
| Archer, Radio Tower | 44 | 37 | 38 | 50 | 50 |
| Clair | 45 | 38-39 | 39-40 | 52 | 52 |
| Rival, Victory Road | 49 | 41 | 42 | 56 | 56 |
| Will | 50 | 42 | 43 | 57 | 57 |
| Koga | 51 | 42-43 | 43-44 | 58 | 58 |
| Bruno | 52 | 43-44 | 44 | 58 | 58 |
| Karen | 54 | 43-44 | 44-45 | 59 | 59 |
| Lance | 56 | 44-45 | 45-46 | 60 | 60 |

**Before patch 0025, an even team fell well behind.** It was 4 to 7 levels under each Johto boss's average
and 11 to 12 under by the Elite Four. Keeping all six at the bosses' average took about 4,000 to 5,000 wild
KOs. Only a single Pokémon taking every KO kept up.

**A modern Exp. Share** (the rest of the party getting half as much) was the other option considered. It
matches the early bosses, but from Chuck on it runs 3 to 7 levels over. hg-engine has no option for it
either. Doubling the experience was chosen instead.

None of these counts:
- the Lucky Egg (Goldenrod, from four badges)
- the Rare Candies sold in Celadon in the post-game
- trainers met again by phone

**The Rare Candies are a way past the post-game grind, and meant as one.** Celadon's Department Store sells
them for ₽3,000. Taking a team of six from 74, where Kanto's trainers leave it after Blue, to the second
round's Lance (86) is 72 Rare Candies, about ₽216,000, and on to Red (93) 42 more, about ₽126,000. The
story bot, which buys nothing and loses half its money at each whiteout, had about ₽195,000 by the Elite
Four and ₽460,000 after Kanto. So a player can pay instead of the roughly 580 wild battles on Mt. Silver, or
do some of each. Celadon's other held items (₽10,000 to ₽25,000) are well within that money and stay as
they are.
