# Changelog

Release numbers belong to the hack. They aren't the FireRed ROM's own
versions (v1.0 and v1.1, "Rev 1"). Each release lists the pull requests that
made it, so you can see exactly what changed.

**Saves:** the "Saves" line under each release says whether a save from the
previous release keeps working. In short, saves made on **release 7 or later**
carry over to the current release. Older saves need a new game.

## Release 9 (2026-11-05)
Pull requests: [#25](https://github.com/RTyH-Code/Personal-Projects/pull/25)

- **Challenge settings:** a menu on the first morning in your room lets you
  switch on Nuzlocke mode, level caps, no items in battle, and the Set battle
  style (locked).
- **Nuzlocke mode:**
  - Only the first wild Pokémon in each area can be caught, with the dupes
    and shiny clauses.
  - Fainting is permanent.
  - Blacking out ends the run.
- **Repel prompt:** when a Repel wears off, the game offers to use another.
- **Modern shiny odds:** 1 in 4,096. After you become Champion, Prof. Oak's
  aide gives you the Shiny Charm (about 1 in 1,365).
- Tools: `exp_budget.py` (trainer Exp. against the level caps) and
  `save_check.py` (save compatibility between releases).
- **Saves:** release 8 saves carry over. An existing save can't switch on the
  challenge rules, because the menu only appears at the start of a new game.
  The level caps can still be switched on at Viridian City. With the new
  shiny odds, a handful of Pokémon you already own may now show as shiny.

## Release 8 (2026-11-05)
Pull requests: [#22](https://github.com/RTyH-Code/Personal-Projects/pull/22), [#23](https://github.com/RTyH-Code/Personal-Projects/pull/23), [#24](https://github.com/RTyH-Code/Personal-Projects/pull/24)

- **Audit and balance pass:**
  - Modern boss movesets from Lt. Surge on, peak teams with the later
    evolutions, and AI fixes.
  - The newer held evolution items now need five badges.
- **Leech Life:** low-level trainers and egg moves no longer get it early.
- **Level caps:**
  - Battle Exp. can't overshoot the cap.
  - Both Day Cares respect the cap.
  - Rare and Special Candy now say when a Pokémon is at the cap.
- **Saves:** release 7 saves carry over.

## Release 7 (2026-11-05)
Pull requests: [#19](https://github.com/RTyH-Code/Personal-Projects/pull/19), [#20](https://github.com/RTyH-Code/Personal-Projects/pull/20), [#21](https://github.com/RTyH-Code/Personal-Projects/pull/21)

- **Later evolutions:**
  - 29 Pokémon, including Weavile, Magnezone, Togekiss, the
    Eeveelutions, Gallade and Froslass.
  - New evolution items, held-item and move-based evolution methods, and a
    raised species limit.
- **Saves:** older saves don't carry over. The higher species limit made
  the Pokédex records in the save one byte bigger.

## Release 6 (2026-11-04)
Pull requests: [#16](https://github.com/RTyH-Code/Personal-Projects/pull/16), [#17](https://github.com/RTyH-Code/Personal-Projects/pull/17), [#18](https://github.com/RTyH-Code/Personal-Projects/pull/18)

- **Later moves:**
  - 143 moves from later generations in three batches, including new battle
    systems (switching moves, field effects and entry hazards).
  - A badge-gated modern move tutor.

## Release 5 (2026-11-04)
Pull requests: [#12](https://github.com/RTyH-Code/Personal-Projects/pull/12), [#13](https://github.com/RTyH-Code/Personal-Projects/pull/13), [#14](https://github.com/RTyH-Code/Personal-Projects/pull/14), [#15](https://github.com/RTyH-Code/Personal-Projects/pull/15)

- **Modern abilities:**
  - Three ability slots, including hidden abilities.
  - New abilities, and modern behaviour for the Gen 3 ones.

## Release 4 (2026-11-04)
Pull requests: [#11](https://github.com/RTyH-Code/Personal-Projects/pull/11)

- **Fairy type:** the modern type chart, retyped Pokémon and six Fairy moves.

## Release 3 (2026-11-04)
Pull requests: [#10](https://github.com/RTyH-Code/Personal-Projects/pull/10)

- HM field moves without teaching them.
- Hidden Power's type and power shown in the IV/EV editor.
- Optional level caps.

## Release 2 (2026-11-02)
Pull requests: [#9](https://github.com/RTyH-Code/Personal-Projects/pull/9)

- **Post-game nature and ability coach.**
- **Guide pages:** peak trainer prep, the type chart and the move list.

## Release 1 (2026-11-01)
Pull requests: [#1](https://github.com/RTyH-Code/Personal-Projects/pull/1), [#3](https://github.com/RTyH-Code/Personal-Projects/pull/3), [#5](https://github.com/RTyH-Code/Personal-Projects/pull/5), [#7](https://github.com/RTyH-Code/Personal-Projects/pull/7), [#8](https://github.com/RTyH-Code/Personal-Projects/pull/8)

- **First release:**
  - Quality-of-life changes and the physical/special split.
  - Modern stats, moves and learnsets.
  - The IV/EV editor.
  - Every Pokémon obtainable, with post-game legendaries.
  - The move relearner, Deoxys formes, peak trainers and the true endgame.
- A patch for FireRed v1.1 (Rev 1), plus the spoiler guide and Pokédex
  compendium.
