# Changelog

## Unreleased

- Cliff Cave's Rock Smash Pokémon are back at the levels they had before
  v1.1, Krabby Lv. 23-30 and Kingler 32-36 (patch 0035). v1.1 put them in
  Chuck's band (26-29), but the cave's map script moves its rocks aside
  until the Champion is beaten, so they are post-game, like the Super Rod,
  which kept its levels.

## v1.3

- Three Gym Leader rematches lose the piece that carried them (patch 0034).
  Played with smart turns, every rematch fell to the second-round set by its
  top level but these three:
  - Clair's Garchomp has Crunch in place of Swords Dance, as Lance's did in
    v1.0, and her Flygon Stone Edge and Dragonite Fire Punch, both in place
    of Dragon Dance;
  - Sabrina's Gardevoir has Calm Mind and her Gallade Night Slash, both in
    place of Hypnosis (her lead, Mr. Mime, keeps it);
  - Misty's Milotic has Recover in place of Hypnosis, and her Gyarados Ice
    Fang in place of Dragon Dance, as Blue's and Lance's Gyarados.

  Sabrina now falls on the second try at her top level and Misty on the
  first. Clair still beats the set there and stays the hardest rematch: a
  player can bring Ice moves for her, and the rematches are optional.

This changes three trainers' teams only. A save made in v1.2 on Route 29
loaded in v1.3, won two wild battles, and the game saved again
(`playtest/save_carry.py`, which now counts a battle as won when it ends on
the same map, however many turns it took).

## v1.2

- The Goldenrod Department Store's 4F sells the evolution items in tiers by
  badges, each from about where final evolutions of its kind come by level
  (patch 0033). Before, every stone and older trade item was on sale from
  Goldenrod, at two badges, which put Steelix, Exeggutor, Starmie and the
  Eeveelutions in reach before Whitney:
  - from the start: Moon, Sun and Oval Stones, the Deep Sea Tooth and Scale;
  - with four badges: Fire, Water, Thunder, Leaf and Ice Stones, King's
    Rock, Up-Grade, Prism Scale;
  - with six: Metal Coat, Dragon Scale, Dusk, Dawn and Shiny Stones (the
    Shiny Stone was sold after Chuck's badge), Black Augurite;
  - with seven, as before: the Peat Block, Protector, Electirizer,
    Magmarizer, Dubious Disc, Reaper Cloth, Razor Claw and Razor Fang.
  Prices are even: ₽3,000 for the stones and older items (King's Rock was
  ₽10,000, the Deep Sea items ₽200), ₽5,000 for the newer ones (the Razor
  Claw was ₽15,000). Selling them back gives half, as for any item. The
  original ways of getting each are unchanged.

This changes the shop and item prices only. A save made in v0.9 on Route 29
loaded in v1.2, won two wild battles, and the game saved again
(`playtest/save_carry.py`). As in v1.1, the save the last check left took
over 30 turns on one battle, on v1.1 as on v1.2.

## v1.1

- Fishing, Rock Smash and Headbutt in Johto follow the same bands as the
  walking and surfing levels (patch 0032), each from where a player can first
  use it:
  - the Good Rod, had in Olivine after Surf, meets each water's surfing
    levels (was Lv. 20 everywhere; now 26-29 up to Cianwood, 30-34 for Pryce,
    34-38 for Clair, 37-42 on Route 45, 45-49 before the League);
  - Rock Smash by the Ruins of Alph and Dark Cave follows Morty, Lv. 21-24
    (was 3-15), and Cianwood's and Cliff Cave's follow Chuck, 26-29 (were
    17-32 and 23-36);
  - Headbutt trees up to Ilex Forest, where Headbutt is had, follow Whitney,
    Lv. 16-19 (were 2-12); later ones follow their area's walking band, as
    far as Routes 26 and 27 at 45-50 (were 28-32). The rarer special trees
    are two levels over their area's band.
  The Old Rod (Lv. 10, had before Falkner) and the Super Rod (Lv. 40, a
  post-game item from Kanto) are unchanged.

This changes encounter and Headbutt data only. A save made in v0.9 on Route
29 loaded in v1.1, won two wild battles, and the game saved again
(`playtest/save_carry.py`). The save v1.0's check left lost its second battle's
count there, taking 36 turns, and did the same on v1.0: most likely its Pokemon's
strongest move had run out of PP over the earlier checks.

## v1.0

- Lance's second-round Garchomp has Crunch in place of Swords Dance (patch
  0031). Played with smart turns, his second round beat the bot's sets in all
  fifteen battles, at Lv. 88 and at 95 with two different sets, Garchomp
  taking three or four Pokemon each time, which put him above Red. The rest
  of his team keeps its combos.

This changes trainer data only. A save made in v0.9 on Route 29 loaded in
v1.0, won two wild battles, and the game saved again (`playtest/save_carry.py`).

## v0.9 (playtest build)

- Routes 47 and 48 and Cliff Cave follow Chuck, like the rest of the land
  around Cianwood (patch 0030). v0.7 and v0.8 left them out as post-game
  areas, but Cliff Edge Gate opens off Cianwood, which a player reaches by
  surfing before Chuck, and Route 47's trainers are Lv. 22-29. Route 48 is
  now Lv. 27-29 (was 23-29), Cliff Cave 26-28 (was 21-26), and Route 47's
  water 26-29 (was 10-29). Route 47's grass (36-46) and the Cliff Edge Gate's
  water were already above and stay.

This changes encounter data only. A save made in v0.8 on Route 29 loaded in
v0.9, won two wild battles, and the game saved again (`playtest/save_carry.py`).

## v0.8 (playtest build)

- Pokémon met surfing in Johto are in line with the land beside them (patch
  0029). The water had kept HeartGold's own levels, Lv. 10-29 at most towns
  and routes, 5-23 at the Lake of Rage, 2-23 at Blackthorn. Each water table
  now follows the boss a player faces next when they can first surf there:
  before Morty, who gives Surf, and on to Cianwood it is 26-31 (Chuck's
  band); Route 42, Mt. Mortar, Route 43 and the Lake of Rage 30-36; Route 44,
  Blackthorn, Dragon's Den and the Whirl Islands 34-40; Route 45 and Dark
  Cave's Route 45 side 37-42. Fishing, Rock Smash and the post-game areas are
  unchanged.

This changes encounter data only. A save made in v0.7 on Route 29 loaded in
v0.8, won a wild battle, and the game saved again.

## v0.7 (playtest build)

- Wild Pokémon in Johto's side areas are in line with the main path beside
  them (patch 0028): the Ruins of Alph's chambers at Lv. 14 (were 5), the
  Bell Tower at 34-37 and the Whirl Islands at 35-38 (were 23-29), Route 45
  and Dark Cave's Route 45 side at 37-42 (were 23-31). Each follows the boss
  a player faces next when going there, in the same band as patch 0027.

This changes encounter data only. A save made in v0.6 on Route 29 loaded in
v0.7 and won a wild battle; a save from v0.4 at the same spot loaded, won
two, and the game saved again.

## v0.6 (playtest build)

- Wild Pokémon in the grass and caves on Johto's main path are a little
  under the boss after them (patch 0027): Routes 30 and 31 are Lv. 7-9, up
  from 2-5, Route 34 is 18-19, Routes 42 and 43 are 30-34, Route 44 and the
  Ice Path 34-38. Keeping a team at each boss's average took about 180 wild
  battles before Falkner and 160 before Jasmine; now no stretch needs more
  than about 60 (`playtest/LEVEL_CURVE.md`). Route 29, Route 46, surfing,
  fishing and the optional areas (Bell Tower, Whirl Islands, the lower floors
  of Union Cave and Slowpoke Well) are unchanged.

This changes encounter data only. A save made in v0.5 on Route 29 loaded in
v0.6; two wild battles were won from it, and the game saved again.

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
