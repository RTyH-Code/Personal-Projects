# FireRed QoL + Hard

A quality-of-life, modernization and difficulty hack built on the pret/pokefirered decompilation.

## Quality of life
- Running Shoes work from the start (hold B).
- New games default to Fast text and the "Set" battle style.
- TMs are reusable, like in later generations. They can't be sold or tossed.
- HM moves can be forgotten at any time.
- Trade evolutions without trading:
  - Kadabra, Machoke, Graveler and Haunter evolve at Lv. 37.
  - Use King's Rock on Poliwhirl or Slowpoke, Metal Coat on Onix or Scyther,
    Dragon Scale on Seadra, Up-Grade on Porygon, and Deep Sea Tooth or
    Deep Sea Scale on Clamperl, the same way you use an evolution stone.
- Celadon Department Store 4F sells every evolution item: all stones,
  including the Moon and Sun Stones, plus the trade items above.
- Pokémon from Johto and Hoenn can evolve before you have the National Dex.

## IV/EV editor
On a Pokémon's summary, go to the **POKéMON SKILLS** page and press **START**.

| Button | Action |
|---|---|
| Up / Down | Choose a stat |
| A | Switch between the IV and EV columns |
| Left / Right (IV column) | Set the IV (0–31) |
| Left / Right (EV column) | Move 4 EVs out of the stat into the pool / from the pool into the stat |
| START | Save. Only allowed when the EV pool is 0 |
| B | Cancel without saving |

You can set IVs freely. EVs can only be moved between stats, so the total
you earned never goes up. Each stat is capped at 255. The editor works for
party and PC Pokémon, but not during battles, trades or link play.

## Modern battle mechanics
- **Physical/special split.** Each move has its own category (from Gen 4
  onward), so Shadow Ball is special and Fire Punch is physical. Thick Fat now
  also halves Attack against Fire/Ice moves.
- **Modern base stats.** For example, Pidgeot has 101 Speed, Dugtrio 100
  Attack and Golem 120 Attack.
- **Modern move power, accuracy and PP.** For example, Flamethrower and
  Thunderbolt are 90 power, Leech Life is 80 and Knock Off is 65. Fury Cutter
  is capped at 160 power, as in modern games. Move *effects* are still Gen 3.
- **Modern level-up learnsets**, taken from the newest generation that has
  each Pokémon (Gen 9, then 8, then 7), limited to moves that exist in Gen 3.
- Types are unchanged. There is no Fairy type.

## Every Pokémon is obtainable
All 386 Pokémon can be caught, evolved or bred in a single FireRed save:
- About 130 new wild slots in places that fit each Pokémon. New Pokémon only
  take slots from species that are common on that table.
- All nine starters are wild: Bulbasaur (Route 25), Charmander (Route 4),
  Squirtle (Route 24), Cyndaquil (Kindle Road), Totodile (Cape Brink),
  Torchic (Mt. Ember), Chikorita (Five Isle Meadow), Treecko (Pattern Bush)
  and Mudkip (Ruin Valley).
- LeafGreen exclusives, Johto Pokémon and Hoenn Pokémon are spread through
  Kanto and the Sevii Islands.
- Altering Cave holds all of its Mystery Gift species at once.

### Legendaries (after your first Hall of Fame entry)
| Pokémon | Where | How |
|---|---|---|
| Mew | Pokémon Mansion B1F, top-left room | Overworld sprite |
| Celebi | Viridian Forest, north-east clearing | Overworld sprite |
| Raikou | Power Plant, large middle room | Overworld sprite |
| Entei | Mt. Ember, path to the summit | Overworld sprite |
| Suicune | Cape Brink, south shore | Overworld sprite |
| Regirock / Regice / Registeel | Tanoby Liptoo / Weepth / Dilford Chamber | Examine the north wall of the innermost room |
| Kyogre | Seafoam Islands B3F | Examine the deep pool from its south shore |
| Groudon | Mt. Ember Ruby Path B3F | Examine the north wall of the first room |
| Rayquaza | Sevault Canyon | Examine the wall at the very top of the canyon |
| Latias | Outcast Island | Examine the cave wall on the island's north side |
| Latios | Memorial Pillar | Examine the north wall above the pillar |
| Jirachi | Mt. Moon B2F | Examine the north wall of the large north-west room |
| Lugia / Ho-Oh | Navel Rock | Mystic Ticket (received at the Hall of Fame) |
| Deoxys | Birth Island | Aurora Ticket (received at the Hall of Fame) |

If you run or knock out a legendary, it stays there for another try.
Catching it removes it. Before the Hall of Fame, examining one of the hidden
spots shows a hint.

## Difficulty
- Every Gym Leader has a new, larger team with max IVs, better moves and a held item.
- Every other trainer's levels are scaled by 1.15x.
- Regular trainers have at least ~18 IVs. The Elite Four, Champion, Rival and Giovanni have max IVs.
- Every trainer uses the smart battle AI.

## Playing it

You need your own **Pokémon FireRed (USA, v1.0)** ROM. No ROM is included here.
Its SHA-1 should be `41cb23d8dccc8ebd7c649cd8fbb58eeace6e2fdc`.

1. Download `FireRed-QoL-Hard.bps`.
2. Apply it to your ROM with a BPS patcher, such as
   [Rom Patcher JS](https://www.marcrobledo.com/RomPatcher.js/) or Floating IPS.
3. Play the patched ROM in any GBA emulator, such as mGBA.

Patched ROM SHA-1: `ed53f5a4450f87f94d86d47d9e0fea19e4be2257`

Start a new game. Saves from earlier versions of this hack aren't supported.

## Building from source

The source changes are git patches on top of
[pret/pokefirered](https://github.com/pret/pokefirered) commit `ce6406d`.

```bash
git clone https://github.com/pret/pokefirered && cd pokefirered
git checkout ce6406d
git am /path/to/firered-qol-hard/source-patches/*.patch
make        # needs agbcc + arm-none-eabi binutils; see pret's INSTALL.md
```

The generator scripts that produced the data changes are in `tools/`. They're
also included in the patches under `tools/hack/`. Each one runs once against
unmodified pret data:
- `difficulty.py`: gym teams, trainer levels and IVs, AI.
- `modernize.py <pokemon-showdown>/data`: split categories, stats, moves and
  learnsets. It reads Pokémon Showdown's data files as text and never runs them.
- `encounters.py`: wild placements. It checks that all 386 Pokémon are obtainable.
- `legendaries.py`: legendary events, flags and the Hall of Fame tickets.
