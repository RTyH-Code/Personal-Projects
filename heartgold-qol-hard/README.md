# HeartGold QoL + Hard

A quality-of-life, modernization and difficulty hack for Pokémon HeartGold,
following the same recipe as [FireRed QoL + Hard](../firered-qol-hard/README.md).
It is built on [hg-engine](https://github.com/BluRosie/hg-engine).

**Status: playtest build (v0.1).** Everything described below is in the
patch. The battles, maps, legendaries, wild Pokémon and shops have been
checked by automated playtesters, but nobody has played the story from start
to finish yet. See the [changelog](CHANGELOG.md).

## Playing it

You need your own US Pokémon HeartGold ROM (game code `IPKE`, SHA-1
`4fcded0e2713dc03929845de631d0932ea2b5a37`). The ROM is not in this
repository and never will be.

1. Download `HeartGold-QoL-Hard-v0.1.xdelta`.
2. Apply it to the ROM with an xdelta patcher such as Delta Patcher or
   xdelta UI, or on a command line:

   ```bash
   xdelta3 -d -s heartgold-usa.nds HeartGold-QoL-Hard-v0.1.xdelta HeartGold-QoL-Hard.nds
   ```

3. The patched ROM is 256 MB, twice the original's size, and its SHA-1 is
   `6106acf7680c406ebf2b042034b32f8217c4b116`. It has been run in DeSmuME;
   other emulators and flashcarts are untried.

Start a new game: saves from the original game or from other hacks will not
work properly. The [spoiler guide](guide/README.md) lists where everything
is.

This hack is free and always will be. hg-engine's terms require that, and
that its credits are reproduced: see [CREDITS-hg-engine.md](CREDITS-hg-engine.md).

## What's changed so far

- Running Shoes work from the start (hold B). The man in Cherrygrove City
  still hands you a pair after his tour.
- New games default to Fast text. You can still change it in Options.
- Every legendary and mythical Pokémon can be caught; see
  [Legendary Pokémon](#legendary-pokémon).
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
  | From the start | Fire, Water, Thunder, Leaf, Ice, Moon, Sun, Dusk and Dawn Stones, Oval Stone, King's Rock, Metal Coat, Dragon Scale, Up-Grade, Deep Sea Tooth, Deep Sea Scale, Prism Scale, Black Augurite |
  | After beating Chuck | Shiny Stone |
  | With seven badges | Peat Block, Protector, Electirizer, Magmarizer, Dubious Disc, Reaper Cloth, Razor Claw, Razor Fang |

  The Ice Stone is there because hg-engine evolves Eevee into Glaceon with
  it; Leafeon uses the Leaf Stone, and Magneton and Nosepass the
  Thunder Stone. The stock, the badge requirement and the prices are a
  first pass and will be revisited when the difficulty is balanced.
- **Held items for money:** the Celadon Department Store 4F counter also
  sells seventeen held items from the original games. Leftovers, the three
  Choice items, Life Orb and Focus Sash cost ₽25,000 and the rest ₽10,000.
  Celadon is past the Champion, so this is a post-game shop.
- **Berries and PP restorers:** the Goldenrod Department Store 3F counter
  also sells Oran and the status berries from the start; Sitrus, Lum and
  Ether at 4 badges; the type-resist berries and Elixir at 6; Max Ether, Max
  Elixir and Max Revive at 8.
- **Poké Marts stock up a badge sooner:** Great Ball, Revive and Super
  Repel at 2 badges; Hyper Potion, Ultra Ball, Full Heal and Max Repel at 4;
  Max Potion at 6. Full Restore stays at 8.
- **Prices:** the game has one price per item, so the items above also sell
  for half their new price. Lists and prices are in
  [guide/ITEMS.md](guide/ITEMS.md).

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
ROM, and the overworld playtester has since bought every item on the shop's
list with no badges and with all of them.

## Difficulty

The levels, IVs, AI and every boss team are in.

- **Level curve.** Trainers and wild Pokémon in Johto are unchanged up to
  Lv. 8, then rise to 1.15× by Lv. 18. Each boss's highest level:

  | Boss | Original | Now | Boss | Original | Now |
  |---|---|---|---|---|---|
  | Falkner | 13 | 14 | Pryce | 34 | 39 |
  | Bugsy | 17 | 19 | Clair | 41 | 47 |
  | Whitney | 19 | 22 | Elite Four | 42–47 | 48–54 |
  | Morty | 25 | 29 | Lance | 50 | 58 |
  | Chuck | 31 | 36 | Blue | 60 | 78 |
  | Jasmine | 35 | 40 | Red | 88 | 95 |

  With their hand-built teams (below) Whitney, Chuck, Jasmine and Pryce
  sit at 24, 34, 38 and 42, so the gyms rise in the intended order.
- **Boss teams.** Every boss from Falkner to Red has a new team: the Johto
  and Kanto Gym Leaders, your rival, the Team Rocket executives, the Kimono
  Girls, both Elite Four rounds, Lance, Blue, Red and the Gym Leader
  rematches. The full teams, with items and moves, are in
  [guide/BOSSES.md](guide/BOSSES.md) (spoilers).
  - Johto Pokémon come first, the ace included; Kanto Pokémon fill in
    where Johto has nothing for the theme, and Hoenn or Sinnoh ones only
    round a team out (Morty's Duskull and Drifblim, Jasmine's Mawile,
    Clair's Altaria, Gabite and Flygon).
  - Teams grow: Falkner 3, Bugsy 4, Whitney 4, Morty 5, Chuck 5, then six
    for Jasmine, Pryce, Clair, each of the Elite Four and Lance.
  - Every boss Pokémon holds an item and has a chosen moveset. Every move
    is one that Pokémon can learn at its level (level-up, a TM or HM in the
    game, and from Morty on Gen 4 egg and tutor moves), except Whitney's
    Miltank keeping Milk Drink.
  - From Chuck on, boss Pokémon have natures and full EV spreads.

  | Boss | Ace | Team |
  |---|---|---|
  | Falkner | Noctowl 14 | Natu, Murkrow |
  | Bugsy | Scyther 19 | Spinarak, Pineco, Yanma |
  | Whitney | Miltank 24 | Furret, Dunsparce, Stantler |
  | Morty | Mismagius 29 | Duskull, Haunter, Drifblim, Gengar |
  | Chuck | Heracross 34 | Primeape, Hitmontop, Machoke, Poliwrath |
  | Jasmine | Steelix 38 | Mawile, Magneton, Forretress, Skarmory, Scizor |
  | Pryce | Mamoswine 42 | Delibird, Sneasel, Jynx, Dewgong, Lapras |
  | Clair | Kingdra 47 | Dragonair, Altaria, Gabite, Gyarados, Flygon |
  | Will | Xatu 51 | Farigiraf, Wobbuffet, Slowking, Exeggutor, Espeon |
  | Koga | Crobat 52 | Ariados, Qwilfish, Forretress, Weezing, Muk |
  | Bruno | Machamp 53 | Hitmontop, Hitmonlee, Hitmonchan, Steelix, Annihilape |
  | Karen | Houndoom 55 | Honchkrow, Weavile, Gengar, Umbreon, Tyranitar |
  | Lance | Dragonite 58 | Gyarados, Aerodactyl, Charizard, Kingdra, Dragonite |
- **Your rival** uses only Johto Pokémon: Sneasel, the Zubat line, the
  Mareep line, Misdreavus, the Larvitar line (from the Goldenrod Tunnel
  on) and his starter. They grow with him: Crobat, Weavile, Ampharos and
  Mismagius by Victory Road, Tyranitar in the post-game.
- **Post-game bosses** (each highest level):

  | Boss | Lv. | Boss | Lv. |
  |---|---|---|---|
  | Lt. Surge | 64 | Blue | 76 |
  | Sabrina, Erika | 66 | Rival at the Indigo Plateau | 76 |
  | Janine, Misty | 68 | Johto leader rematches | 78–82 |
  | Brock | 70 | Kanto leader rematches | 82–83 |
  | Blaine | 72 | Elite Four, second round | 80–84 |
  | Rival at Mt. Moon | 66 | Blue's rematch, Lance's second round | 86, 88 |
  | | | Red | 95 |

  The Kanto leaders keep their Kanto signatures with Johto Pokémon added
  (Sudowoodo, Politoed, Lanturn, Ampharos, Sunflora, Qwilfish, Espeon,
  Magcargo, Houndoom). The rematch teams use anything that fits the
  leader's type, Hoenn and Sinnoh Pokémon included. Red keeps his team.
- **Other Kanto trainers** are 1.3× their original levels.
- **Kanto wild Pokémon** are post-game strength instead of starting again
  at Lv. 2. The areas keep their original order:

  | Area | Original | Now |
  |---|---|---|
  | Route 1, Viridian Forest | 2–7 | 46–48 |
  | Mt. Moon, Routes 3–4 | 5–12 | 47–50 |
  | Routes 5–11, Diglett's Cave | 12–29 | 50–57 |
  | Routes 13–18 | 22–32 | 54–58 |
  | Seafoam Islands | 26–40 | 56–62 |
  | Cerulean Cave | 37–49 | 61–66 |
  | Route 28, Mt. Silver | 15–51 | 62–70 |

  Surfing, Rock Smash, fishing and Headbutt trees in Kanto follow the same
  scale. A wild
  Pokémon that is past a level-up evolution appears evolved (Pidgeot and
  Raticate on Route 1, not a Lv. 46 Pidgey). Stone, held-item and
  friendship evolutions are left as they were, and Larvitar's line stops
  at Pupitar, so there is no wild Tyranitar.
- Johto fishing, Johto's Headbutt trees and the Safari Zone are unchanged.
  Routes 26 and 27 count as Johto here, as they do for the other wild levels.
- **IVs:** every trainer Pokémon has at least about 18 in each stat; Gym
  Leaders, the Elite Four, the Champion, your rival, Red and the Rocket
  bosses have 31.
- **AI:** every trainer uses the smartest move-choice settings.

Every boss has been fought in the emulator by the battle playtester; see
[playtest](playtest/README.md) for how the fights ranked. The built trainer
data was also decoded to confirm the teams, items, abilities, natures and
EVs were written as specified.

## Pokémon availability

Every non-legendary Pokémon family can be obtained in Johto, before the
Elite Four, without the Safari Zone, the post-game radio or trading. The
weak ones turn up early and the strongest late. Nothing that was already in
an area was removed; the new Pokémon take slots that repeated a species.

| When | Area | Added |
|---|---|---|
| Before badge 2 | Route 29 | Zigzagoon, Bidoof |
| | Routes 30–31 | Ledyba (morning), Weedle, Kricketot (night), Pachirisu |
| | Route 46, Dark Cave (Route 31 side) | Spinda, Sableye |
| | Sprout Tower | Chingling |
| | Route 32 | Poochyena, Wingull, Ekans, Surskit |
| | Union Cave | Mawile, Cubone, Barboach (Old Rod) |
| | Route 33 | Nincada, Meditite |
| | Ilex Forest | Kecleon, Pikachu, Budew, Illumise and Volbeat (night) |
| Badges 2–4 | Route 34 | Skitty, Glameow, Shellos, Jigglypuff, Ralts, Corphish (Old Rod) |
| | Route 35, National Park | Stunky, Gulpin, Chatot, Lotad, Buneary, Carnivine |
| | Routes 36–37 | Vulpix, Shinx, Electrike, Bonsly, Plusle, Minun, Houndour (night), Cyndaquil |
| | Burned Tower | Shuppet, Drifloon, Murkrow (night), Slugma, Duskull, Torkoal, Rotom |
| Badges 4–6 | Routes 38–39 | Meowth, Spoink, Zangoose, Kangaskhan, Chikorita, Totodile |
| | Routes 40–41, Cianwood, Whirl Islands | Wailmer, Carvanha (surfing); Finneon, Clamperl, Luvdisc, Relicanth (Good Rod) |
| | Ruins of Alph (outer area), Cliff Cave | Baltoy, Bronzor, Lunatone, Solrock, Nosepass |
| | Routes 47–48 | Skorupi, Trapinch, Tropius, Cacnea |
| Badges 6–7 | Route 42, Mt. Mortar | Numel, Seviper, Bulbasaur, Buizel (surfing), Makuhita, Whismur, Clefairy, Croagunk, Grimer, Aron |
| | Route 43, Lake of Rage | Castform, Mime Jr., Charmander, Porygon, Feebas (Good Rod) |
| Badges 7–8 | Route 44 | Elekid, Squirtle, Munchlax, Chansey |
| | Ice Path | Delibird, Snorunt, Snover, Sneasel, Spheal |
| | Route 45, Dark Cave (Blackthorn side) | Skarmory, Absol, Hippopotas, Swablu, Treecko, Torchic, Bagon, Teddiursa, Gible |
| | Mt. Mortar (above the waterfall), Tohjo Falls | Riolu, Larvitar, Mudkip |
| | Bell Tower | Spiritomb |
| Before the Elite Four | Routes 26–27, Victory Road | Turtwig, Chimchar, Piplup, Beldum |

The starters, Kangaskhan, Munchlax, Trapinch, Riolu, Larvitar and Beldum
are 4% encounters; Rotom, Porygon, Chansey, Bagon, Gible, Spiritomb,
Skorupi and Absol are 1%. The rest are 4–10%. Eevee, Togepi, Tyrogue, Lapras, Sudowoodo and the Bug-Catching
Contest's Scyther and Pinsir are where HeartGold already had them.

- **Fossils:** a scientist in the Ruins of Alph Research Center revives
  fossils, the same way the Pewter Museum does (hand one over, leave, come
  back). Smashing rocks at the Ruins of Alph can turn up the Helix and Dome
  Fossils and the Old Amber; in Cliff Cave, the Claw, Root, Skull and Armor
  Fossils.
- The Safari Zone is unchanged.
- One Shiny Stone can still be picked up early in the National Park.

The fossil reviver was played through in the emulator (Old Amber to
Aerodactyl). The wild placements were checked against the data, not by
finding each Pokémon in play.

## Legendary Pokémon

Every legendary and mythical Pokémon up to Arceus can be caught, with no
trading and no events. The ones HeartGold already had stay where they
were, at levels that fit the hack's curve. The missing ones stand in the
overworld like Articuno or Mewtwo: talk to one to fight it. If you catch it,
it is gone for good. If it faints or you run, it is back the next time you
enter the area.

Already in the game:

| Pokémon | Where | Level |
|---|---|---|
| Red Gyarados | Lake of Rage | 34 (was 30) |
| Raikou, Entei | Roaming Johto | 46 (was 40) |
| Ho-Oh | Bell Tower | 52 (was 45) |
| Suicune | Route 25 | 60 (was 40) |
| Latias | Roaming Kanto | 60 (was 35) |
| Articuno, Zapdos, Moltres | Seafoam Islands, Route 10, Mt. Silver | 65 (was 50) |
| Lugia | Whirl Islands | 70 |
| Kyogre | Embedded Tower | 70 (was 50) |
| Rayquaza | Embedded Tower, once you own Groudon and Kyogre | 75 (was 50) |
| Mewtwo | Cerulean Cave | 80 (was 70) |

Sudowoodo and the Union Cave Lapras are level 22, and the two Snorlax
level 65.

Added:

| When | Pokémon | Where | Level |
|---|---|---|---|
| After the Champion | Latios | Roams Kanto; Steven releases it with Latias | 60 |
| | Regirock, Regice, Registeel | Ruins of Alph, in the item rooms behind three of the puzzle chambers (north-east, south-east, north-west) | 60 |
| | Regigigas | Ruins of Alph, the item room behind the south-west chamber, with the three Regis in your party | 75 |
| | Uxie | Union Cave B2F, on the water | 60 |
| | Mesprit | Lake of Rage, on the water | 60 |
| | Azelf | Dragon's Den, on the water | 60 |
| | Heatran | Cinnabar Island | 65 |
| | Cresselia | Mt. Moon Square, at the pond | 65 |
| | Celebi | Ilex Forest, beside the shrine | 65 |
| | Shaymin | National Park, below the fountain | 65 |
| | Manaphy | Whirl Islands B2F, on the water | 65 |
| 16 badges | Groudon | Embedded Tower, in Kyogre's room once Kyogre is caught | 70 |
| | Dialga, Palkia, Giratina | Ruins of Alph, the underground hall | 75 |
| After Red | Arceus | Ruins of Alph, the underground hall | 80 |
| | Mew | Mt. Silver summit | 80 |
| | Jirachi | Route 25, at the cape | 80 |
| | Deoxys | Route 3 | 80 |
| | Darkrai | Dark Cave (Route 45 side) | 80 |

"16 badges" means after Professor Oak has seen all sixteen. Phione comes
from breeding Manaphy.

The overworld playtester has gone to all of them at their real places: each
is absent until its condition is met and then starts the right battle at the
right level. Catching, running away and coming back were tested by hand on a
test build.

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
| Trainer levels, IVs and AI | Done: `tools/hack/difficulty.py` |
| Johto and League boss teams | Done: `tools/hack/boss_teams.py` |
| Kanto leaders, Blue, Red, second Elite Four round and rematch teams | Done: `tools/hack/boss_teams.py` |
| Johto wild levels | Done: `tools/hack/wild_levels.py` |
| Kanto wild levels | Done: `tools/hack/kanto_wild.py`, `tools/hack/kanto_headbutt.py` |
| Every non-legendary Pokémon obtainable in Johto | Done: `tools/hack/encounters.py`, `tools/hack/fossil_reviver.py` |
| Legendary encounters | Done: `tools/hack/legendaries.py` |
| Trade evolutions without trading | Done: `tools/hack/trade_evos.py` |
| Evolution item shop | Done, to be rebalanced |
| Field HMs without teaching them | Done |
| Held-item shop, berry and consumables stand, earlier mart stock | Done: `tools/hack/shops.py` |
| Spoiler guide generated from the data | Done: `tools/spoiler_guide.py` writes [guide/](guide/README.md) |
| Unattended playtester | Done: battle tester and overworld tester, see [playtest](playtest/README.md). No story playthrough bot. |

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

The release patch is made from such a build, in a fresh work directory, with
`tools/make_patch.sh`. v0.1 was built this way from all seventeen patches.

To confirm the result boots, without opening an emulator window:

```bash
pip install py-desmume
```

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/boot_check.py build/hg-engine/test.nds boot-shots
```
