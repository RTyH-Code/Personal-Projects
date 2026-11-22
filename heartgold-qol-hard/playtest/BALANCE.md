# Boss balance: what the story bot found

The story bot has played the whole story, from the bedroom to the Hall of
Fame, using boss team sets: a team built for each boss from what a player can
catch and teach by then (`team_sets.py`). This page brings its boss results
together and lists ways to fix the fights that came out too hard. The fixes
picked are in source patch 0022; the next section shows how they played.

The tables come from `python3 balance.py`, run over `results/battles.jsonl`.

## How to read the numbers

- **The bot plays worse than a player.** The game's own trainer AI picks its
  moves. It never switches out of a bad matchup, never uses items in battle,
  and lets a Swords Dance or Dragon Dance user set up freely. Setup sweepers
  and sleep look stronger here than they will against a person.
- **The bot also gets help a player wouldn't.** Before Clair, the rival on
  Victory Road and every League room, the harness heals the party where it
  stands, standing in for potions. Between League rooms it also gives back
  used berries. From the Kanto runs on, it heals before every Gym Leader and
  Rocket executive too (see the playtest README), so later records start
  boss fights at full health where earlier ones may not have.
- **The bot's teams are not a player's.** The Johto and League sets only
  used Pokémon caught and evolved by level, and a short list of TMs (not the
  Goldenrod Department Store's Fire Blast, Thunder, Blizzard or Focus Blast,
  nor Victory Road's Earthquake). They leaned on type matchups, such as Bugs
  against Psychic types that are also weak to them through their second type
  (Heracross, Ariados). A player would more likely bring bulky Pokémon that
  take hits and hit back hard for neutral damage: Snorlax, Blissey,
  Tyranitar, Umbreon, Scizor, all of which the hack makes available by the
  League. So a hard result here can be the set's fault as much as the
  boss's. The Kanto sets are built the player's way.
- **The samples are small and mixed.** Most fights were played a handful of
  times. The records span several team versions and bot fixes. A low rate
  across many battles, with the same Pokémon doing the damage each time, is
  the signal to trust.

## What patch 0022 changed, and how it played

The aim: story bosses are a challenge, not a headache. Each keeps its
threats but loses the combo that turned the fight on one setup turn. The
post-game second rounds and rematches keep the hard combos.

Each stage was played four times on the new teams, from the same save as
before, with one retry after a loss. Pryce, Proton and Petrel were also
played with `STORY_JITTER=600`, a random wait after the save loads. Without
it, those tries replayed the same battle move for move.

| Boss | What changed | Before | After | Ours fainted per win |
|---|---|---|---|---|
| Lance | Aerodactyl leads (Crunch for Curse); Gyarados fourth with a Sitrus Berry | 6 of 30 | 3 of 6 | 4.0 |
| Karen | Tyranitar: Ice Punch for Dragon Dance. Weavile: Razor Claw for Focus Sash | 3 of 26 | 2 of 6 | 5.0 |
| Clair | Gyarados and Kingdra get their own sets; Gabite loses Swords Dance | 2 of 11 | 2 of 6 | 3.5 |
| Koga | Ariados: Black Sludge for Focus Sash | 7 of 13 | 4 of 4 | 2.0 |
| Ariana, Radio Tower | Honchkrow: Sharp Beak for Scope Lens | 1 of 5 | 4 of 6 | 3.5 |
| Pryce | Jynx: Fake Out for Lovely Kiss | 1 of 3 | 8 of 8 | 3.2 |
| Proton, Slowpoke Well | A level higher; a Rattata added | 0 fainted | 4 of 4 | 1.2 |
| Petrel, Radio Tower | A level higher; Weezing leads; a Koffing with a Focus Sash | 0 fainted | 4 of 4 | 0.2 |

The before column counts every battle recorded before; the samples after
are small. Run `python3 balance.py --run rebalance` for the after table, or
`--exclude rebalance` for before. The records labelled `rebalance-0022-rocket`
are the final Proton and Petrel teams. The other `rebalance-0022` records for
those two come from a first draft that only raised levels.

What it shows:

- **Lance, Ariana, Pryce and Koga** now turn on the whole team, not on one
  Pokémon's first turn.
- **Karen and Clair** are still the hardest story fights, and still lose
  more than they win against the bot. Neither has one Pokémon sweeping any
  more: Tyranitar takes two of ours per battle, Gengar two or three. Clair's
  Gyarados and Altaria (Outrage, Sing) share the damage. The bot never
  switches or uses items, so a player should find both fair. If they need
  one more step: Gengar's Wise Glasses for a Black Sludge, and Altaria's
  Sing for Dragon Breath.
- **Proton in the Slowpoke Well** now takes one or two of ours.
- **Petrel** is still easy for a team with a Psychic type. The bot's
  Alakazam, or its Claydol, outspeeds every Koffing and knocks each out in
  one hit. Only a Pokémon that isn't Poison type would change that, at the
  cost of his all-Koffing gimmick.
- **The Kimono Girls** are left as they are, story flavour, not bosses.

## Results

These are the records from before patch 0022. Each row is one boss fight. "Ours fainted per win" counts how many of our
Pokémon fainted in the battles the bot won. The last column counts which of
the boss's Pokémon knocked ours out, over every battle of that fight.

| Boss | Where | Won | Ours fainted per win | Knocked ours out |
|---|---|---|---|---|
| Falkner | Violet Gym | 2 of 2 | 1.0 | Natu 2 |
| Silver | Azalea | 2 of 4 | 4.0 | Bayleef 15, Flaaffy 3 |
| Proton | Slowpoke Well | 1 of 1 | 0.0 | — |
| Bugsy | Azalea Gym | 1 of 1 | 4.0 | one each |
| Whitney | Goldenrod Gym | 4 of 7 | 3.0 | Dunsparce 11, Stantler 8, Miltank 6 |
| Silver | Burned Tower | 3 of 4 | 2.0 | Misdreavus 4, Sneasel 3 |
| Morty | Ecruteak Gym | 1 of 1 | 5.0 | Drifblim 3 |
| Chuck | Cianwood Gym | 1 of 1 | 4.0 | Heracross 2 |
| Jasmine | Olivine Gym | 1 of 1 | 3.0 | one each |
| Petrel | Rocket Hideout | 1 of 1 | 5.0 | Raticate 2 |
| Ariana | Rocket Hideout | 2 of 6 * | 1.5 | Ariados 4, Arbok 2 |
| Pryce | Mahogany Gym | 1 of 3 | 5.0 | Jynx 9, Mamoswine 4, Dewgong 3 |
| Proton | Radio Tower | 4 of 4 | 3.5 | Houndoom 5, Weezing 4 |
| Petrel | Radio Tower | 1 of 1 | 0.0 | — |
| Ariana | Radio Tower | 1 of 5 | 2.0 | Honchkrow 11 |
| Archer | Radio Tower | 2 of 4 | 2.5 | Crobat 5, Houndoom 4, Sneasel 4 |
| Silver | Goldenrod Underground | 1 of 1 | 2.0 | — |
| Clair | Blackthorn Gym | 2 of 11 | 3.5 | Gyarados 16, Gabite 8, Dragonair 8, Flygon 7 |
| Kimono Girls | Ecruteak dance theatre | 10 of 10 | 0.4 | Jolteon 2, Vaporeon 2 |
| Silver | Victory Road | 1 of 3 | 3.0 | Ampharos 3, Crobat 3 |
| Will | League | 15 of 19 | 2.7 | Espeon 15, Wobbuffet 12, Slowking 12 |
| Koga | League | 7 of 13 | 2.3 | Ariados 14, Crobat 14, Qwilfish 8 |
| Bruno | League | 6 of 8 | 3.3 | Annihilape 14 |
| Karen | League | 3 of 26 | 3.7 | Tyranitar 55, Gengar 35, Weavile 24, Houndoom 15 |
| Lance | League | 6 of 30 | 3.8 | Gyarados 49, Aerodactyl 41, Charizard 34, Dragonite 26 |

\* Four of the six Hideout Ariana battles are recorded as losses with only one
of ours fainted. That is the double battle beside Lance, from before the bot's
loss check was fixed. Read it as about even.

Some fights don't point at the boss:

- **The two Victory Road losses** came after the whole cave with no heal.
- **The Azalea rival's Bayleef** swept a party of Rock and Ground types. That
  says more about the party the bot had caught than about the rival.

## The fights to look at

Five fights stand out, ordered by how sure the data is. Two patterns explain
most of it:

- **A guaranteed setup turn.** A Focus Sash on a Swords Dance user, or
  Intimidate on a Dragon Dance user, lets it boost before anything can stop
  it.
- **The same set appearing twice.** Clair's Gyarados and Kingdra are Lance's,
  move for move, ten levels sooner.

### Lance: 6 of 30

**What happens:** Gyarados (Intimidate, Dragon Dance, Wacan Berry) leads. In
most losses it Dragon Danced and knocked out three or four of ours before
anything else of his moved. After that come:

- Aerodactyl, with Focus Sash and Curse, which is a second setup user.
- Charizard.
- The two Dragonites.

**Options, mildest first:**

1. Move Gyarados out of the lead, for example to fourth. He then can't set up
   on whatever leads against him, and the player has seen part of his team
   before it comes out.
2. Give Gyarados a Sitrus Berry in place of the Wacan Berry. Electric moves,
   the plain answer to it, then knock it out in one hit again.
3. Replace Dragon Dance with Thunder Wave or Ice Fang. Gyarados stays
   dangerous but stops snowballing.
4. Replace Aerodactyl's Curse with Rock Slide or Ice Fang. Keep the Sash or
   the setup move, not both.

My pick is 1 + 2. Lance keeps his signature Gyarados, and the fight no longer
turns on its first turn.

### Karen: 3 of 26

**What happens:** Tyranitar (Dragon Dance, Stone Edge, Crunch, Earthquake,
Chople Berry) did the most damage of any single Pokémon in the data: 55 of
ours. The Chople Berry takes the edge off a Fighting move, which is the usual
answer to it. After a Dragon Dance it outspeeds and knocks out everything.
Karen's other threats are:

- Gengar (Wise Glasses, Hypnosis).
- Weavile (Focus Sash, Swords Dance), another guaranteed setup.

**Options:**

1. Tyranitar: replace Dragon Dance with Pursuit or Ice Punch, and keep the
   Chople Berry. It is then a strong wall, not a sweeper.
2. Or keep Dragon Dance and swap the Chople Berry for Leftovers. A Fighting
   or Water move then knocks it out.
3. Weavile: replace the Focus Sash with Life Orb or Razor Claw, so a fast hit
   stops it before it sets up.
4. Gengar: Hypnosis to Destiny Bond or Thunderbolt, or keep Hypnosis and drop
   the Wise Glasses for a Black Sludge or Spell Tag.

My pick is 1 + 3.

### Clair: 2 of 11, before the heal

**What happens:** Clair's Gyarados and Kingdra are exactly Lance's sets.
Gyarados (Intimidate, Dragon Dance, Wacan Berry) did most of the damage: 16
of ours. Flygon and Gabite also carry setup moves (Dragon Dance and Swords
Dance). The bot lost all nine battles until the harness healed the party
before her, standing in for the potions a player would use after her gym
trainers. With the heal both teams won.

**Options:**

1. Give her Gyarados its own set, so the Champion's signature isn't seen ten
   levels early: Waterfall, Crunch, Ice Fang, Thunder Wave, and a Sitrus
   Berry. Do the same for Kingdra: drop Rain Dance for Dragon Pulse or Surf.
2. Keep one setup user in the team (Flygon's Dragon Dance), not three: Gabite
   loses Swords Dance for Fire Fang or Dragon Claw.

My pick is both: 1 and 2.

### Ariana in the Radio Tower: 1 of 5

**What happens:** Honchkrow (Super Luck, Scope Lens, Foul Play, Brave Bird)
knocked out 11 of ours. Super Luck and Scope Lens together add two critical
hit stages, so about half its hits are critical. That ignores our defence
boosts and its own attack drops, so the fight comes down to luck. The same
Pokémon at Lv. 40 (a Murkrow, Hideout) was fine.

**Options:**

1. Swap the Scope Lens for a Sitrus Berry or Sharp Beak. Its critical rate
   drops back to one stage.
2. Or change its ability from Super Luck to Insomnia.

My pick is 1.

### Pryce: 1 of 3

**What happens:** Jynx (Lovely Kiss, Wise Glasses, Ice Beam, Psychic) knocked
out 9 of ours. In one loss it took out all five of ours that were left. It
outspeeds most of a Lv. 42 party and puts the one that can hurt it to sleep.
Mamoswine (Curse) finishes the rest.

**Options:**

1. Replace Lovely Kiss with Fake Out or Ice Shard. Sleep then stays with
   Lapras's Sing, which is less accurate.
2. Or keep Lovely Kiss and swap the Wise Glasses for a Sitrus Berry.

My pick is 1. Three battles is a thin sample, though, so this is a lighter
call than the ones above.

## Worth watching

- **Koga, 7 of 13.** Ariados (Focus Sash, Swords Dance) and Crobat (Hypnosis)
  did most of it. It got much better once the team had held items and
  Bronzong. If Karen's Weavile loses its Sash, Ariados could lose its Sash
  too, to Black Sludge, for the same reason.
- **Whitney, 4 of 7.** Dunsparce (Serene Grace with Rock Slide and Glare)
  flinches or paralyses most of the time: 11 of ours. It is meant to be the
  gym's hard Pokémon, and 4 of 7 is a fair fight for the third gym. If it
  should be softer, swap Rock Slide for Ancient Power or Shock Wave.
- **Archer, 2 of 4.** Within range.

## Maybe too easy

- **The Kimono Girls** were all won at the first try, and three of them
  without one of ours fainting. They are story flavour for the Eeveelution
  theme, not serious bosses, so they stay as they are.
- **Petrel in the Radio Tower** fainted none of ours.
- **Proton in the Slowpoke Well** also fainted none of ours.

The rest of the gyms each have one win in one battle, with three to five of
ours fainted. That is about the hard-mode feel wanted, but one battle each is
a small sample.

## Post-game: Kanto, the second round, and Red

The bot healed before each of these fights and used the Kanto sets
(`team_sets.py`). These are one run each (`postgame-kanto` and `postgame-red`
in `results/battles.jsonl`).

| Fight | Tries | Ours fainted in the win | Note |
|---|---|---|---|
| Lt. Surge | 1 | 2 | |
| Sabrina | 1 | 4 | |
| Erika | 1 | 3 | |
| Misty | 1 | 4 | |
| Janine | 1 | 1 | |
| Brock | 1 | 1 | |
| Blaine | 1 | 2 | |
| Blue | 3 | | Softened after 8 losses: Gyarados has a Sitrus Berry and Ice Fang, not Mystic Water and Dragon Dance (patch 0023) |
| Will, Koga, Bruno, Karen (second round) | 1 each | | |
| Lance (second round) | lost 4 of 4 | | A peak fight: his combos stay on purpose |
| Red | 1 | 5 | Blissey was the last one standing |

Red's team, for the record of who fainted what: Lucario took Lapras, Tyranitar
took Charizard, Electivire took Blastoise, Salamence took Snorlax and Pikachu,
and Blissey took Venusaur after Gliscor fell.

## Johto and the League again, with teams built the player's way

The Johto and League sets were rebuilt the way the Kanto ones were: bulky
Pokémon that hit hard for neutral damage (Snorlax, Tyranitar, Gyarados,
Lanturn, Bronzong, Gardevoir) in place of the type-matchup picks
(`*_v2` in `team_sets.py`, chosen with `STORY_TEAM_<BOSS>=<boss>_v2`). The
checker now also makes sure a set's evolved Pokémon could have learned its
moves before evolving. Each stretch was run from the same saves as before,
healing before each boss, with up to five tries per stage and
`STORY_JITTER=600`. The records are `johto-v2` (the sets as they stand) and
`johto-v2-first` (the versions they replaced) in `results/battles.jsonl`.

| Boss | Before (the earlier sets, after patch 0022 where it changed them) | Player's-way sets | Changed on the way |
|---|---|---|---|
| Falkner, Bugsy, Whitney, Morty, Chuck, Jasmine | first try each | first try each | |
| Pryce | 8 of 8 | first try | Gyarados for Muk: with Muk, won on try 3, Mamoswine finishing both losses |
| Clair | 2 of 6 | first try | |
| Radio Tower and the Underground | Ariana 4 of 6 | every stage first try | Snorlax for Muk: the Underground rival's Mismagius beat the Muk set 4 of 5 |
| Will | 15 of 19 | first try in all 4 runs | |
| Koga | 4 of 4 | first try in all 4 runs | |
| Bruno | 6 of 8 | 1 of 5 | 0 of 5, 0 of 5 and 1 of 3 with the earlier versions |
| Karen | 2 of 6 | 1 of 3 | 1 of 2 with the version before |
| Lance | 3 of 6 | 0 of 5 | 0 of 5 with the version before |

The League set is now Snorlax, Tyranitar, Gardevoir, Lanturn, Azumarill and
Slowbro. It got there one swap at a time:

1. **Slowbro for Lanturn.** Bruno's Hitmonlee and Annihilape swept everyone
   but Gardevoir, and Bruno won 5 of 5.
2. **Azumarill for Walrein.** Annihilape, Ghost and Fighting with a Spell Tag,
   still won 5 of 5, since Slowbro doesn't resist its Ghost moves. With
   Azumarill Bruno fell on try 3, but with no Ice or Electric left Lance won 5
   of 5.
3. **Lanturn back, for Bronzong.** Lance still won 5 of 5, and Bruno fell
   only on try 5.

**Through Clair, the player's-way sets do as well as the type-matchup ones or
better.** The bosses that had needed several tries went down on the first.

**The League is the other way round.** Over Lance's ten losses, Dragonite took
22 of ours, Gyarados 19, Aerodactyl 11 and Kingdra 7. One bulky team can't
cover all five members the way a type-matchup team does: Bruno wants Fairy and
Psychic, and Lance wants Electric and Ice. As before, the bot never switches out
of a bad matchup and never uses items in battle, so a player would do better
here than these League numbers suggest. Whether to soften Lance's first round, as was done
for Blue, is still open.

## Something else found

In `guide/BOSSES.md`, a few rows were broken: the item, moves and nature ran
together. The guide's report writer gave the item 14 characters, and Never
Melt Ice has 15. That is fixed, and the tables regenerated.
