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
| Karen | 53-55 (avg 54) | 0 | 52-53 | 52-53 | 79 | 78 | 21 | 21 |
| Lance | 55-58 (avg 56) | 0 | 53 | 53-54 | 80 | 79 | 45 | 48 |
wild KOs in all, medium fast: 284
wild KOs in all, medium slow: 182

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

Patch 0029 puts the water in the same bands, from where a player can first surf. `walk_test.py`'s surf check on
the build with the test harness met only Pokémon in the new tables on seven of ten areas: Route 34 Tentacool
27-29, Route 41 Tentacruel 29, Route 42 Goldeen and Seaking 32, Route 43 Magikarp 32-33, the Lake of Rage
Magikarp 31-32 and Gyarados 31, Route 44 Poliwag 37-38, Route 45 Magikarp 37-41. In New Bark Town nothing appeared
in 750 steps, on Route 40 a Swimmer stepped in, and at Blackthorn the test couldn't start surfing from the bank it
tried. Run as one batch the check stopped without an error after loading; one area at a time, each ran through.

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
