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

- HM moves can be forgotten at any time.
- TMs are reusable (hg-engine's default).
- New games skip the control and adventure info screens and start at
  Professor Oak.
- Battles run at 60 fps.
- Held items used in battle come back afterwards, except berries.
- Friendship evolutions trigger at 160 friendship instead of 220.
- The Exp. formula scales with level difference, as in recent games.
- Mega Evolution, Primal Reversion and critical captures are switched off.

Only the tutorial skip has been checked in the emulator so far. The others
are hg-engine switches that build cleanly but haven't been played through.

## Plan

The FireRed recipe, and where each part comes from here:

| Part | Source |
|---|---|
| Physical/special split, abilities, natures | Already in HeartGold |
| Fairy type, hidden abilities, later moves, abilities and Pokémon | hg-engine |
| Reusable TMs, forgettable HMs, modern Exp. formula, EV/IV viewer | Done: hg-engine config switches |
| National Dex from the start, with its unlocks moved to story checks | To do: needs code changes |
| Set mode, level cap and no-items rules as player options | Undecided: hg-engine only offers them as fixed rules |
| Harder trainers, Gym Leaders, Elite Four and rematches | To do: `data/Trainers.c` |
| Wild levels and a fixed Johto level curve | To do: `data/Encounters.c` |
| Every non-legendary Pokémon obtainable | To do: encounters, gifts, evolutions |
| Trade and other awkward evolutions without trading | To do: `data/Evolutions.c` |
| Field HMs without teaching them, shops, post-game ladder | To do: code and scripts |
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
