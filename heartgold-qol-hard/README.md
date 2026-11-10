# HeartGold QoL + Hard

A quality-of-life, modernization and difficulty hack for Pokémon HeartGold,
following the same recipe as [FireRed QoL + Hard](../firered-qol-hard/README.md).
It is built on [hg-engine](https://github.com/BluRosie/hg-engine).

**Status: early.** The build pipeline works and the first config switches
are set (see below). Trainers, encounters and everything else are still
unchanged from HeartGold. There is no patch to download.

This hack is free and always will be. hg-engine's terms require that, and
that its credits are reproduced: see [CREDITS-hg-engine.md](CREDITS-hg-engine.md).

## What's changed so far

- Running Shoes work from the start (hold B). The man in Cherrygrove City
  still hands you a pair after his tour.
- New games default to Fast text. You can still change it in Options.
- HM moves can be forgotten at any time.
- TMs are reusable (hg-engine's default).
- New games skip the control and adventure info screens and start at
  Professor Oak.
- Battles run at 60 fps.
- Held items used in battle come back afterwards, except berries.
- Friendship evolutions trigger at 160 friendship instead of 220.
- The Exp. formula scales with level difference, as in recent games.
- Mega Evolution, Primal Reversion and critical captures are switched off.
- **National Dex from the start.** The Pokédex has its National mode from
  the first moment, and Professor Oak rates the national count over the
  phone. What HeartGold unlocks along with the National Dex now waits until
  you become Champion instead, which is when the original game gives you
  the dex:
  - the Tuesday, Thursday and Saturday Bug-Catching Contests with Hoenn and
    Sinnoh bugs, their tougher contestants and the wider first-prize pool;
  - Hoenn Sound and Sinnoh Sound on the Pokégear radio;
  - Baoba's later Safari Zone phone calls;
  - the second Pokéathlon prize list and the Supreme Cup;
  - the Rock Smash rocks in Cliff Cave.
- **HMs without teaching them:** with the HM in your bag and the badge that
  allows it, the move works even if no Pokémon knows it.
  - Cut, Surf, Strength, Whirlpool, Rock Smash, Waterfall and Rock Climb
    work straight from the overworld: face the tree, rock or water and
    press A, as usual.
  - Fly and Flash (TM70) show up in the party menu on every Pokémon that
    could learn them, or on your first Pokémon if none can.
  - The game names a Pokémon as the one using the move: one that knows it
    if there is one, otherwise the first that could learn it, otherwise the
    first in the party.
  - Headbutt, Dig, Teleport and Sweet Scent still have to be known.
- **Trade evolutions without trading:**
  - Kadabra, Machoke, Graveler and Haunter evolve at Lv. 37.
  - Use the item on the Pokémon, the same way you use an evolution stone:

    | Item | Evolves |
    |---|---|
    | King's Rock | Poliwhirl → Politoed, Slowpoke → Slowking |
    | Metal Coat | Onix → Steelix, Scyther → Scizor |
    | Dragon Scale | Seadra → Kingdra |
    | Up-Grade | Porygon → Porygon2 |
    | Dubious Disc | Porygon2 → Porygon-Z |
    | Protector | Rhydon → Rhyperior |
    | Electirizer | Electabuzz → Electivire |
    | Magmarizer | Magmar → Magmortar |
    | Reaper Cloth | Dusclops → Dusknoir |
    | Deep Sea Tooth | Clamperl → Huntail |
    | Deep Sea Scale | Clamperl → Gorebyss |
    | Prism Scale | Feebas → Milotic (the Beauty method still works too) |

    The items keep their held effects.
- **Later evolutions of Johto-era Pokémon:**

  | Evolution | How |
  |---|---|
  | Scyther → Kleavor | Use a Black Augurite |
  | Ursaring → Ursaluna | Level up at night holding a Peat Block |
  | Primeape → Annihilape | Lv. 40 |
  | Stantler → Wyrdeer | Level up knowing Psyshield Bash (learned at Lv. 31) |
  | Girafarig → Farigiraf | Level up knowing Twin Beam (learned at Lv. 32) |
  | Dunsparce → Dudunsparce | Level up knowing Hyper Drill (learned at Lv. 32) |
  | Eevee → Sylveon | Level up knowing a Fairy-type move (Baby-Doll Eyes at Lv. 15) |

  Annihilape and Wyrdeer use different methods from the official games,
  where a move has to be used 20 times; hg-engine doesn't support that.
  Rage Fist isn't implemented in hg-engine, so Annihilape can't learn it.
- **Evolution item shop:** the Goldenrod Department Store 4F clerk sells
  every evolution item alongside the vitamins. The original ways of
  getting them are all still there.

  | When | Items |
  |---|---|
  | From the start | Fire, Water, Thunder, Leaf, Ice, Moon, Sun, Shiny, Dusk and Dawn Stones, Oval Stone, King's Rock, Metal Coat, Dragon Scale, Up-Grade, Deep Sea Tooth, Deep Sea Scale, Prism Scale, Black Augurite |
  | With seven badges | Peat Block, Protector, Electirizer, Magmarizer, Dubious Disc, Reaper Cloth, Razor Claw, Razor Fang |

  The Ice Stone is there because hg-engine evolves Eevee into Glaceon with
  it; Leafeon uses the Leaf Stone, and Magneton and Nosepass the
  Thunder Stone. The stock, the badge requirement and the prices are a
  first pass and will be revisited when the difficulty is balanced.

The tutorial skip, the Running Shoes and the Fast text default have been
checked in the emulator. So have the HM changes, on a save given the HMs
and badges: Surf (on a Chikorita), Fly and Flash in the party menu, Fly
opening the map, and Fly being refused without the badge. Cut, Strength,
Whirlpool, Rock Smash, Waterfall and Rock Climb use the same code but
haven't been tried in play. The other
switches build cleanly but haven't been played through. The National Dex
change was checked by disassembling the built ROM, not by playing to
Champion. The trade evolutions were checked in the built data files, not by
evolving a Pokémon in play. The shop's stock list and badge check are in the built
ROM, but the shop hasn't been visited in play.

## Design rules

- **Pokémon:** the original 493, plus later-generation evolutions and
  pre-evolutions of those (Sylveon, for example). No other later-generation
  Pokémon.
- **Fairy type:** on.
- **No Mega Evolution or Primal Reversion.**

## Plan

The FireRed recipe, and where each part comes from here:

| Part | Source |
|---|---|
| Physical/special split, abilities, natures | Already in HeartGold |
| Fairy type, hidden abilities, later moves, abilities and Pokémon | hg-engine |
| Reusable TMs, forgettable HMs, modern Exp. formula, EV/IV viewer | Done: hg-engine config switches |
| National Dex from the start, with its unlocks moved to a Champion check | Done |
| Set mode, level cap and no-items rules as player options | Undecided: hg-engine only offers them as fixed rules |
| Harder trainers, Gym Leaders, Elite Four and rematches | To do: `data/Trainers.c` |
| Wild levels and a fixed Johto level curve | To do: `data/Encounters.c` |
| Every non-legendary Pokémon obtainable | To do: encounters, gifts, evolutions |
| Trade evolutions without trading | Done: `tools/hack/trade_evos.py` |
| Evolution item shop | Done, to be rebalanced |
| Field HMs without teaching them | Done |
| Shops, post-game ladder | To do: code and scripts |
| Spoiler guide generated from the data | To do: port `spoiler_guide.py` |
| Unattended playtester | To do: py-desmume based |

## Building from source

The hack is hg-engine at commit `dbb3213` plus the git patches in
`source-patches/`. You need your own US HeartGold ROM
(game code `IPKE`, SHA-1 `4fcded0e2713dc03929845de631d0932ea2b5a37`).
The ROM is never stored in this repository.

Install the build requirements (Ubuntu), plus
[rustup](https://rustup.rs/) for one of hg-engine's helper tools:

```bash
sudo apt-get install build-essential cmake git python3-venv pkg-config libpng-dev gcc-arm-none-eabi libnewlib-arm-none-eabi
```

Then build:

```bash
tools/build.sh /path/to/heartgold-usa.nds
```

The first build takes several minutes. It clones hg-engine into `build/`,
applies the patches and writes `build/hg-engine/test.nds`.

To confirm the result boots, without opening an emulator window:

```bash
pip install py-desmume
```

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/boot_check.py build/hg-engine/test.nds boot-shots
```
