# Changelog

## v0.5 (playtest build)

- Wild Pokémon on Routes 26 and 27, at Tohjo Falls and in Victory Road are
  Lv. 45-50, up from 17-41 (patch 0026). A team arrives there at about 50,
  and the old levels gave so little experience that catching up to the
  Elite Four took around 500 wild battles; now it takes about 150
  (`playtest/BALANCE.md`). Pokémon past a level-up evolution appear
  evolved there, as in Kanto: Rapidash, Dodrio, Rhydon, Metang, and the
  Sinnoh and Hoenn starters fully evolved. Fishing is unchanged.

This changes encounter data only. A save made in v0.4 on Route 29 loaded in
v0.5; two wild battles were won from it, and the game saved again.

## v0.4 (playtest build)

- Every battle gives double experience (patch 0025). Beating every trainer on
  the way, a team of six used in turn was 4 to 7 levels under each Johto boss's
  average and 11 to 12 under by the Elite Four; now it is within about 3 levels
  all the way (`playtest/LEVEL_CURVE.md`). This changes game code, not just
  data, so an emulator save state made with an earlier version freezes at the
  next battle. Carry on from the in-game save instead. A save made in v0.3 on
  Route 29 loaded in v0.4 at the same spot; two wild battles were won from it,
  and the game saved again.

## v0.3 (playtest build)

Boss teams only (patches 0022 to 0024). These change trainer data and
nothing kept in a save, so a v0.2 save should carry on, though that has not
been tried.

From the story bot's playthrough (see `playtest/BALANCE.md`). Story bosses
keep their threats but lose the combos that turned a fight on one setup
turn; the post-game teams keep them.

- Lance leads with Aerodactyl (Crunch in place of Curse) and brings Gyarados
  fourth, holding a Sitrus Berry. His Gyarados has Ice Fang and his last
  Dragonite Thunder Punch, both in place of Dragon Dance, and that Dragonite
  holds a Sitrus Berry in place of Leftovers (patch 0024). His second round is
  unchanged.
- Karen's Tyranitar has Ice Punch in place of Dragon Dance; her Weavile
  holds a Razor Claw in place of a Focus Sash.
- Clair's Gyarados and Kingdra have their own sets instead of Lance's, and
  her Gabite loses Swords Dance.
- Koga's Ariados holds Black Sludge in place of a Focus Sash.
- Ariana's Honchkrow in the Radio Tower holds a Sharp Beak in place of a
  Scope Lens.
- Pryce's Jynx has Fake Out in place of Lovely Kiss.
- Blue's Gyarados holds a Sitrus Berry in place of a Mystic Water and has
  Ice Fang in place of Dragon Dance (patch 0023). He is the eighth Kanto
  badge, before the Elite Four's second round and Red; his rematch is
  unchanged.
- Proton in the Slowpoke Well has a Rattata and is a level higher.
- Petrel in the Radio Tower is a level higher, leads with Weezing (Shadow
  Ball), and one Koffing holds a Focus Sash; Protect is gone for Pain Split.
- The boss guide's tables are fixed where an item name ran into the moves.

## v0.2 (playtest build)

Follow-ups from an audit of v0.1. A save made in v0.1 at the start of the game
loads in v0.2.

- Late-game trainers' Pokémon evolve where their level allows.
- Wild Pokémon no longer hold items from later games.
- An old man in the Ruins of Alph Research Center tells where the added
  legendary Pokémon are, a tier at a time.
- The Lucky Egg is sold in Goldenrod from four badges; Rare Candies, the
  Ability Capsule and the Ability Patch are sold in Celadon.

## v0.1 (playtest build)

The first patch. Everything in the README is in; nothing has been played
from start to finish yet, so expect rough edges and tell me about them.

- Quality of life: National Dex from the start, Running Shoes from the
  start, Fast text by default, forgettable HMs, field HMs used from the bag,
  60 fps battles, the tutorial screens skipped.
- Evolutions: trade evolutions by level or by using the item, later-game
  evolutions of Johto and Kanto Pokémon, an evolution item shop.
- Difficulty: raised and smoothed levels, better IVs and AI on every
  trainer, hand-built boss teams from Falkner to Red, a Johto-heavy rival.
- Availability: every non-legendary family in Johto before the Elite Four, a
  fossil reviver at the Ruins of Alph, every legendary and mythical Pokémon
  catchable, Kanto wild Pokémon at post-game levels.
- Shops: held items in Celadon, berries and PP restorers in Goldenrod, Poké
  Marts that stock up a badge sooner.
- A spoiler guide in `guide/`.
