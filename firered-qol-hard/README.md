# FireRed QoL + Hard

A quality-of-life and difficulty hack built on the pret/pokefirered decompilation.

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

Patched ROM SHA-1: `1834dcc2bf4ad690ce856e7f69e7b448fa13060e`

Start a new game. The text speed and battle style defaults only apply to new saves.

## Building from source

The source changes are git patches on top of
[pret/pokefirered](https://github.com/pret/pokefirered) commit `ce6406d`.

```bash
git clone https://github.com/pret/pokefirered && cd pokefirered
git checkout ce6406d
git am /path/to/firered-qol-hard/source-patches/*.patch
make        # needs agbcc + arm-none-eabi binutils; see pret's INSTALL.md
```

`difficulty.py` is the script that generated the trainer and gym changes. To
re-tune them, edit its constants and run it from the repo root
(`python3 tools/hack/difficulty.py`) on a checkout without patch 0001's
trainer changes.
