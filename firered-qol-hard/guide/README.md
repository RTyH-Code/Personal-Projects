# FireRed QoL + Hard: spoiler guide

**Spoilers ahead.** Generated from the game's data, so it matches the patched ROM.

## Where to start
New to the hack? These pages, roughly in the order you'll want them:

1. [Pokédex](POKEDEX.md): plan your team. Every Pokémon (all 386, plus the later evolutions the hack adds) with stat
   ranges, abilities, type defenses, evolutions, where to find it and full learnsets.
2. [Wild encounters](ENCOUNTERS.md): what each area has, by grass, cave, surf, Rock Smash and fishing, with rates and
   levels. ★ marks additions. In a Nuzlocke, this is where you plan your first encounters.
3. [Trainers](TRAINERS.md): every Gym Leader, Elite Four and Champion team (rounds 1–2 and peak), then every other
   trainer by location. Check the next gym before you go in.
4. [Items](ITEMS.md): item balls, hidden items, gifts and shop stock by location, including the stock that grows as you
   progress.
5. [VS Seeker rematches](REMATCHES.md): every rematch team and when it unlocks, the intended way to catch up on levels.

After the Elite Four:

6. [Peak trainer prep](PEAK.md): the Lv. 100 Gym Leader and Elite Four teams, with real stats, what they're weak to and
   suggested counters.
7. [Trainer Tower](TOWER.md): every challenge floor by floor, with the types you'll face and suggested counters.

Reference:

- [Types and moves](TYPES.md): the type chart (with Fairy), moves whose physical/special category changed, and every
  move with its power, accuracy, PP and effect.
- [Pokémon](POKEMON.md): gift, static and legendary Pokémon, in-game trades, changed evolutions, base stat and move
  changes.

## Nuzlocke planning
How many new encounter areas (map sections) you can reach before each gym, going in the usual order. The Old Rod
opens fishing before Lt. Surge, and Surf opens after Koga. The level cap is the Gym Leader's strongest Pokémon. "Above
the cap" lists areas where a wild Pokémon (not counting fishing) can be higher than that. You can still catch and use it,
but it won't gain Exp. until the cap rises. Gift Pokémon (your starter, Eevee, Lapras, the fossils and so on) come on top.

| Before | New areas | Areas in all | Level cap | Highest wild level | Above the cap |
|---|--:|--:|--:|--:|---|
| Brock | 4 | 4 | 16 | 6 | — |
| Misty | 5 | 9 | 23 | 14 | — |
| Lt. Surge | 9 | 18 | 28 | 31 | Diglett's Cave B1F |
| Erika | 6 | 24 | 35 | 25 | — |
| Koga | 10 | 34 | 45 | 38 | — |
| Sabrina | 6 | 40 | 47 | 46 | — |
| Blaine | 1 | 41 | 51 | 44 | — |
| Giovanni | 7 | 48 | 54 | 48 | — |

Regenerate with `python3 tools/hack/spoiler_guide.py <output dir>` from the source tree.
