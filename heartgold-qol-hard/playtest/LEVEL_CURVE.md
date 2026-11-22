# The level curve

What level does a player's team reach by each boss without grinding? The story bot can't answer that, since
it swaps in a team at the boss's top level before each fight. `level_curve.py` works it out from the game's
data instead:
- **The trainers:** it splits the story into stretches, one per boss, with the maps a player passes through
  on the way. Every trainer on those maps is beaten once, in order, and each boss's own team counts towards
  the next stretch.
- **The formula:** experience follows the hack's scaled formula, which gives more for beating higher-level
  Pokémon and less for lower ones.
- **Checked against the game:** in the emulator, a Violet Gym trainer's Spearow gave exactly the predicted
  99 experience. Falkner's team gave 1,042 against a predicted 1,054.

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

## Without grinding

| Boss | Their levels | Trainers on the way | Even team, medium fast | Even team, medium slow | One carry, medium fast | One carry, medium slow | Wild KOs to reach their average, medium fast | The same, medium slow |
|---|---|---|---|---|---|---|---|---|
| Falkner | 11-14 (avg 12) | 12 | 6-7 | 8 | 10 | 12 | 422 | 203 |
| Proton, Slowpoke Well | 15-18 (avg 16) | 17 | 10-11 | 12-13 | 17 | 18 | 375 | 196 |
| Bugsy | 16-19 (avg 18) | 4 | 12-13 | 14-15 | 19 | 21 | 348 | 222 |
| Rival, Azalea | 18-21 (avg 19) | 0 | 12-13 | 14-15 | 20 | 22 | 233 | 156 |
| Whitney | 21-24 (avg 22) | 14 | 15-16 | 17-18 | 24 | 26 | 214 | 149 |
| Rival, Burned Tower | 24-27 (avg 25) | 21 | 19-20 | 21 | 30 | 32 | 110 | 68 |
| Morty | 26-29 (avg 28) | 4 | 21 | 23 | 33 | 34 | 280 | 232 |
| Chuck | 31-34 (avg 32) | 36 | 26 | 27-28 | 40 | 41 | 129 | 96 |
| Jasmine | 35-38 (avg 36) | 0 | 26-28 | 28-29 | 41 | 42 | 465 | 431 |
| Petrel, Rocket HQ | 36-39 (avg 37) | 20 | 29-30 | 31 | 45 | 46 | 0 | 0 |
| Ariana, Rocket HQ | 37-40 (avg 38) | 4 | 30 | 31-32 | 46 | 47 | 130 | 108 |
| Pryce | 38-42 (avg 40) | 5 | 31-32 | 32-33 | 48 | 49 | 430 | 408 |
| Proton, Radio Tower | 41-43 (avg 42) | 11 | 33-34 | 34-35 | 51 | 52 | 319 | 301 |
| Petrel, Radio Tower | 43-44 (avg 43) | 1 | 34-35 | 35-36 | 53 | 54 | 116 | 111 |
| Rival, Goldenrod Tunnel | 41-44 (avg 42) | 6 | 35-36 | 37 | 55 | 55 | 0 | 0 |
| Ariana, Radio Tower | 43-45 (avg 44) | 3 | 36-37 | 37-38 | 56 | 56 | 40 | 35 |
| Archer, Radio Tower | 43-46 (avg 44) | 0 | 37 | 38 | 57 | 57 | 0 | 0 |
| Clair | 44-47 (avg 45) | 12 | 38-39 | 39-40 | 59 | 59 | 0 | 0 |
| Rival, Victory Road | 48-50 (avg 49) | 25 | 41 | 42 | 63 | 63 | 299 | 299 |
| Will | 49-51 (avg 50) | 0 | 42 | 43 | 64 | 64 | 102 | 104 |
| Koga | 50-52 (avg 51) | 0 | 42-43 | 43-44 | 65 | 65 | 120 | 123 |
| Bruno | 51-53 (avg 52) | 0 | 43-44 | 44 | 66 | 66 | 135 | 141 |
| Karen | 53-55 (avg 54) | 0 | 43-44 | 44-45 | 67 | 67 | 363 | 372 |
| Lance | 55-58 (avg 56) | 0 | 44-45 | 45-46 | 68 | 68 | 412 | 426 |
wild KOs in all, medium fast: 5042
wild KOs in all, medium slow: 4181

**An even team of six falls well behind.** It is 4 to 7 levels under each Johto boss's average and 11 to 12
under by the Elite Four. Keeping all six at the bosses' average would take about 4,000 to 5,000 wild KOs
over the game. Only a single Pokémon taking every KO keeps up, and by the League it runs 10 levels over.
A starter (medium slow) stays a level or two ahead of a medium fast team all the way, since medium slow
needs less experience early on.

**This also changes how to read the boss results.** The story bot's teams were set at each boss's top
level (`team_sets.py`). A player who doesn't grind will arrive 6 to 14 levels below that, so the bosses
will feel harder than `BALANCE.md` suggests.

## Possible fixes

The even team of six again, with experience given out more freely:
- **Modern Exp. Share:** the Pokémon that fought gets the full amount, and the rest of the party half as
  much, each at its own level. hg-engine has no option for this, so it would need a patch.
- **Double or 1.5x experience:** every KO gives more.

| Boss | Their average | Modern Exp. Share, medium fast | Modern Exp. Share, medium slow | Double experience, medium fast | Double experience, medium slow | 1.5x experience, medium fast | 1.5x experience, medium slow |
|---|---|---|---|---|---|---|---|
| Falkner | 12 | 9 | 10-11 | 8 | 9-10 | 7-8 | 8-9 |
| Proton, Slowpoke Well | 16 | 15 | 16 | 13-14 | 14-16 | 12-13 | 13-14 |
| Bugsy | 18 | 17 | 18-19 | 14-16 | 16-18 | 13-15 | 15-16 |
| Rival, Azalea | 19 | 18 | 19-20 | 15-16 | 17-18 | 14-15 | 16-17 |
| Whitney | 22 | 21 | 23 | 18-19 | 20-21 | 17-18 | 19 |
| Rival, Burned Tower | 25 | 26-27 | 28 | 23 | 25 | 22 | 23 |
| Morty | 28 | 29 | 30 | 25 | 26-27 | 23-24 | 25 |
| Chuck | 32 | 35 | 36 | 31-32 | 32-33 | 29 | 30-31 |
| Jasmine | 36 | 36-37 | 37-38 | 32-33 | 33-34 | 29-31 | 31-32 |
| Petrel, Rocket HQ | 37 | 40 | 41 | 35 | 36 | 33 | 34 |
| Ariana, Rocket HQ | 38 | 41 | 42 | 36 | 37 | 33-34 | 34-35 |
| Pryce | 40 | 42 | 43 | 37-38 | 38 | 34-35 | 35-36 |
| Proton, Radio Tower | 42 | 45 | 46 | 39-40 | 40-41 | 37 | 37-38 |
| Petrel, Radio Tower | 43 | 47 | 47-48 | 41-42 | 42-43 | 38-39 | 39-40 |
| Rival, Goldenrod Tunnel | 42 | 48 | 49 | 42 | 43 | 39-40 | 40 |
| Ariana, Radio Tower | 44 | 49 | 50 | 43-44 | 44 | 40-41 | 41-42 |
| Archer, Radio Tower | 44 | 50 | 50 | 44 | 44-45 | 41 | 42 |
| Clair | 45 | 52 | 52 | 45-46 | 46-47 | 42-43 | 43-44 |
| Rival, Victory Road | 49 | 56 | 56 | 49 | 49-50 | 46 | 46-47 |
| Will | 50 | 57 | 57 | 50 | 50-51 | 46-47 | 47 |
| Koga | 51 | 58 | 58 | 50-51 | 51 | 47 | 47-48 |
| Bruno | 52 | 58 | 58 | 51-52 | 51-52 | 47-48 | 48-49 |
| Karen | 54 | 59 | 59 | 52-53 | 52-53 | 48-49 | 49 |
| Lance | 56 | 60 | 60 | 53 | 53-54 | 49-50 | 49-50 |

- **Double experience** keeps the team within about 3 levels under the bosses' average through Johto, and
  2 to 3 levels under by the League. That's still a little below the bot's test teams, which is about right for a hard mode.
- **The modern Exp. Share** matches the early bosses, but from Chuck on it runs 3 to 7 levels over, and by
  the League 4 to 7.
- **1.5x experience** still leaves the team 3 to 7 levels short from Pryce on.

Not counted, in any of these:
- wild battles met on the way
- the Lucky Egg (Goldenrod, from four badges)
- the Rare Candies sold in Celadon in the post-game
- trainers met again by phone

So a player can make up some of the gap. The fixes above are about how much of it they should have to.
