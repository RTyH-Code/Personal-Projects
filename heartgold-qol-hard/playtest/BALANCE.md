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
here than these League numbers suggest.

### Lance softened (patch 0024)

As with Blue, Lance's Gyarados lost Dragon Dance for Ice Fang. His last
Dragonite lost it for Thunder Punch, and holds a Sitrus Berry in place of
Leftovers. His second round is unchanged. The League was played again on the
new build from the Victory Road save (`lance-0024` in `results/battles.jsonl`):

| Set | Lance before | Lance after |
|---|---|---|
| The earlier League set (Ampharos, Gardevoir, Bronzong, Jynx, Machamp, Gyarados) | 3 of 6 | 3 of 8 |
| The player's-way set | 0 of 10 | 0 of 7 |

The change made little difference. With no Dragon Dance, the rebuilt team
still lost each battle in 12 to 16 of Lance's moves. That is about one and a
half moves per KO, and Gyarados and the Dragonites took 2 or 3 of ours each. The earlier
set, built around type matchups, still wins about one in three. So the
rebuilt set lacks the damage and the Electric and Ice coverage this fight
needs. Dragon Dance was not the cause. Lance stays as he is now: winning about one in three
with a type-matchup team seems fair for the last story boss, and a player who
switches and uses items should do better than the bot.

## The bosses at a player's levels

Every run above swapped in a team at the boss's top level. `LEVEL_CURVE.md`
shows that a player who beats every trainer on the way, but doesn't grind,
arrives lower, even with double experience. So each Johto boss and Will were
played again with the team set to the even team's level (medium fast, the
low end) from that table. The bot's `STORY_LEVEL_<SET>=<level>` setting
devolves anything that evolves above that level, and drops moves it couldn't
know yet. These are the earlier type-matchup sets, from the same saves as
before, healing before each boss, with up to five tries and
`STORY_JITTER=600`. The records are `player-levels` in
`results/battles.jsonl`, with the team's level as `team_level`.

| Boss | Set's level before | Player's level | Before | At the player's level | Took the most of ours |
|---|---|---|---|---|---|
| Falkner | 14 | 8 | 2 of 2 | 0 of 5 | Natu 16, Murkrow 9 |
| Bugsy | 19 | 14 | first try | 1 of 3 | Scyther 7, Pineco 6 |
| Whitney | 24 | 18 | 4 of 7 | 0 of 5 | Miltank 13, Stantler 6, Dunsparce 6 |
| Morty | 29 | 25 | first try | first try | |
| Chuck | 34 | 31 | first try | 0 of 5 | Heracross 12, Hitmontop 7 |
| Jasmine | 38 | 32 | first try | 1 of 3 | Scizor 6 |
| Pryce | 42 | 37 | 8 of 8 | 0 of 5 | Mamoswine 13, Dewgong 8 |
| Radio Tower | 46 | 42 | Ariana 4 of 6 | stuck before Archer | a Koffing grunt in the Underground warehouse, 5 times |
| Clair | 47 | 45 | 2 of 6 | 0 of 5 | Altaria 11, Gyarados 9 |
| Will | 58 | 51 | 15 of 19 | 0 of 5 | Farigiraf 10, Espeon 9 |

**At the levels a player gets to, the bot loses almost every boss.** Only
Morty fell on the first try. Bugsy and Jasmine took three tries, and the rest
won five of five. The gap matters more than its size suggests. Chuck at 3
levels down and Clair at 2 went from wins to 0 of 5, because their teams'
aces (Heracross, Altaria and Gyarados) now outspeed and take two or three of
ours each. Before Falkner the gap is 6 levels, which no team of starters and
early catches makes up.

Some of this is the bot. It never switches out of a bad matchup and never
uses items in battle, and these sets were picked for the top level, not
for 3 to 7 levels under. But the same bot with the same sets won all but
Pryce, Clair and the League's harder fights at the top level, so what
changed is the level. A player who doesn't grind will find most Johto
bosses a wall, and needs the 600 to 1,000 wild KOs `LEVEL_CURVE.md` counts
to get past them.

### The bulky sets at a player's levels

The same runs with the sets built the player's way (`*_v2`), at the same
levels (`player-levels-v2`). Most taught moves drop out at these levels, so
the sets fight with their level-up moves, and the League's Tyranitar is a
Pupitar.

| Boss | Player's level | Type-matchup sets | Bulky sets | Took the most of ours |
|---|---|---|---|---|
| Falkner | 8 | 0 of 5 | first try | |
| Bugsy | 14 | 1 of 3 | first try | |
| Whitney | 18 | 0 of 5 | 0 of 5 | Miltank 17, Dunsparce 8 |
| Morty | 25 | first try | first try | |
| Chuck | 31 | 0 of 5 | 0 of 5 | Heracross 16, Poliwrath 8 |
| Jasmine | 32 | 1 of 3 | 0 of 5 | Skarmory 9, Steelix 8, Scizor 6 |
| Pryce | 37 | 0 of 5 | 0 of 5 | Mamoswine 15, Dewgong 5 |
| Radio Tower | 42 | stuck before Archer | every boss first try | |
| Clair | 45 | 0 of 5 | 1 of 5 | Flygon 11, Gyarados 4 |
| Will | 51 | 0 of 5 | 0 of 5 | Exeggutor 9, Espeon 7 |

**Bulk carried Falkner, Bugsy, the Radio Tower and (just) Clair.** Whitney,
Chuck, Jasmine, Pryce and Will still won every time. Their aces hit hard
enough to sweep a team a few levels down, however it's built.

### How far up the bulky sets need to be

Those five, and Clair, were played again with the bulky sets a level or two
higher (`player-levels-ladder`). The wild KOs are what `level_curve.py`'s
model says an even team of six (medium fast; medium slow in brackets) needs
on top of every trainer on the way, grinding in the stretch's grass.

| Boss | Their average | Lowest level won | Tries there | Wild KOs to get there |
|---|---|---|---|---|
| Whitney | 22 | 21 | first try | 95 (10) |
| Chuck | 32 | 32 | 1 of 5; first try at 33 | 54 (15) to 33 |
| Jasmine | 36 | 35 | 1 of 2 | 77 (67) |
| Pryce | 40 | 39 | 1 of 3 | 1 (0) |
| Clair | 45 | 46 | 1 of 4; first try at 47 | 0 |
| Will | 50 | 55 | first try; 0 of 5 at 53 | 439 (440) |
| Koga | 51 | 55 | 1 of 5 | |
| Bruno | 52 | not at 55 | 0 of 5 | |

**Through Clair the grind is fair.** The bot wins at or a level under each
boss's average, which costs at most about 100 wild KOs before a gym, and
none for Pryce and Clair.

**The League is the exception.** The bot needed 55, five over Will's average,
and still lost to Bruno there, as it did with this set at 58. Getting from
50 to 55 takes about 440 wild KOs. Most of that is because the
grass before the League is low: Routes 26 and 27 have Pokémon at 32 to 37,
which give a team at 50 little under the scaled formula. Some of it is the
bot: the League is where not switching costs it most.

**So the wild Pokémon before the League were raised (patch 0026).** Routes 26
and 27, Tohjo Falls and Victory Road go from Lv. 17-41 to 45-50, keeping
their order, with Pokémon past a level-up evolution appearing evolved. By
the same model, bringing a team from 50 to 55 there now takes about 145
wild KOs in place of about 490, and to Lance's average about 45 in place of
160. The Elite Four are unchanged.

**Checked in the game on v0.5.** From a fresh boot of the v0.5 build with the
test harness, `walk_test.py`'s wild and surf checks were run on the six
areas, ten wild Pokémon each:

| Area | Met | Matches the table |
|---|---|---|
| Route 26, walking | Sandslash 48, Raticate 48, Rapidash 49, Infernape 49 (8 met) | yes |
| Route 26, surfing | Tentacruel 48-49 | yes |
| Route 27, surfing | Tentacruel 46 | yes |
| Tohjo Falls, walking | Golbat 47, Raticate 47, Swampert 47 | yes |
| Victory Road 1F and 2F | Golbat 49, Graveler 49, Donphan 49, Metang 50, Onix 50 | yes |

On Route 27's grass and Victory Road 3F a trainer saw the player where the
test landed, and Tohjo Falls' water couldn't be reached from the bank it
tried; 3F has the same levels as 1F and 2F in the ROM's data. A party at
Lv. 50 on Route 27's grass, away from its trainers, beat a Lv. 48 Raticate
for 2,680 experience, exactly what `level_curve.py`'s formula gives, so the
grind numbers above hold in the game. A longer grind there wasn't
measured: the harness's party fainted to a Lv. 48 Quagsire, and it can't
send in the next Pokémon.

## Does the bot switch or use items?

The bot gives the player's side the game's own trainer AI, with the expert
flags. That AI can switch, and it uses items from its trainer's four item
slots. The player's slots are empty, so `STORY_BATTLE_ITEMS` now fills them
before each trainer battle. Each battle's record also lists the player's
switches and the items used.

Bruno was played with the bulky League set at Lv. 55, from the save after
Koga: ten battles carrying nothing, and seven carrying three Hyper Potions
and a Full Heal. **The AI never switched and never used an item.** All 17
were lost. Its switching is the original game's, which acts only in
corner cases. Its items, by the Gen 4 rules, are only used at a quarter of
the Pokémon's HP or less, a window our Pokémon at these levels mostly skip
from one hit to the next. So the bot still plays like a player who never
switches or heals, and the League numbers above are harsher than a
player's would be. To change that, the bot has to make those choices
itself, through the battle menus.

## The bot playing its own turns

So now the bot does. With `STORY_SMART=1` it keeps the player's own command
menu, party screen and bag instead of handing them to the AI. Each turn it
reads both Pokémon from the battle's data, and `smart.py` chooses one of
three things:

- **Heal:** at 40% HP or under it uses a potion from the bag, at most twice
  on each Pokémon. The bag's potion is stocked to six of what a player would
  have by then: Potions under Lv. 15, Super Potions under 35, Hyper Potions
  after. This is test harness only, like the heal before a boss.
- **Switch:** it switches when the foe's types hit its Pokémon super
  effectively, none of its moves hit back super effectively, and a teammate
  takes the foe's types for half or less. That teammate comes in; it never
  switches two turns running, and at most three times a battle.
- **Fight:** otherwise it picks Fight, and the trainer AI picks the move as
  before.

After a faint it sends in the teammate the foe hurts least. Everything else
is as before: the same saves, the bulky sets at a player's levels, a heal
before each boss, up to five tries, and `STORY_JITTER=600`. The records are
`player-levels-smart` in `results/battles.jsonl`.

| Boss | Team's level | Plain turns (the AI's) | Smart turns | Took the most of ours |
|---|---|---|---|---|
| Whitney | 18 | 0 of 5 | 0 of 5 | Miltank 21, Furret 6 |
| Chuck | 31 | 0 of 5 | 1 of 4 | Heracross 10, Poliwrath 7 |
| Jasmine | 32 | 0 of 5 | first try | |
| Pryce | 37 | 0 of 5 | first try | |
| Clair | 45 | 1 of 5 | first try | |
| Will | 51 | 0 of 5 | 0 of 5 | Espeon 11, Exeggutor 6 |
| Bruno | 55 | 0 of 15 | first try | |

**Playing its own turns, the bot beats five of the seven.** Pryce, Clair and
Bruno fell on the first try, and Chuck on the fourth. Jasmine fell on the
first try after one fix: in an earlier run the bot's own switch pressed just
above the Shift button and stalled after three losses. Almost all of the
gain is from potions, which the bot used two to four times in each win. It
switched once in all these battles, Gyarados out for Quagsire against
Jasmine's Magneton. With these teams a teammate that resists the foe's types
is rarely left.

**Two still win every time.**
- **Whitney:** at Lv. 18 the team is six under her top level. The heals
  bought little: her Miltank took 21 of ours over five battles, and the team
  knocked out at most two of hers. At Lv. 21 the plain bot already beat her
  on the first try (above). Patch 0027 makes those levels about 22 wild
  battles away, so the fair test is the level after a short grind.
- **Will:** at Lv. 51 his Espeon and Exeggutor still swept the team. The plain
  bot needed Lv. 55 for him, and patch 0026 puts that about 145 wild battles
  from where the team arrives.

So the losses at a player's levels were mostly the bot's, not the bosses'. A
player who heals beats most bosses at the level they arrive at, and needs a
short grind for Whitney and the League.

### Whitney and the League after a short grind

Both again with smart turns: Whitney at Lv. 21, about 22 wild battles away
since patch 0027, and the League at Lv. 53, about 75 wild battles away
since patch 0026.

| Boss | Team's level | Smart turns | Took the most of ours |
|---|---|---|---|
| Whitney | 21 | 1 of 5 | Stantler 11, Miltank 7 |
| Will | 53 | 1 of 2 | Exeggutor 4 |
| Koga | 53 | 1 of 3 | Muk 5, Qwilfish 4 |
| Bruno | 53 | first try | |
| Karen | 53 | first try | |
| Lance | 53 | 0 of 5 | Gyarados 14, Dragonite 10, Aerodactyl 4 |

**After a short grind the Elite Four fall, and Whitney does on the last of
five tries.** Lance doesn't. The first run reached him, but a switch that
didn't go through left the bot's party order wrong, and it stalled there.
After that fix, Lance was played five times from the save after Karen and
won every one.

That matches the bulky League set's record against him: 0 of 10 at Lv. 58
(above), against 3 of 8 for the type-matchup set. The set lacks the Electric
and Ice coverage his Gyarados and Dragonites call for, and Lv. 53 is two
under his lowest (55). A player picking a team for Lance would bring that
coverage, so this is a test of the set more than of Lance.

**With the type-matchup League set (Ampharos, Gardevoir, Bronzong, Jynx,
Machamp, Gyarados), Lance still wins.** The same League at Lv. 53, smart
turns:

| Boss | Type-matchup set | Bulky set (above) | Took the most of ours (type-matchup) |
|---|---|---|---|
| Will | first try | 1 of 2 | |
| Koga | first try | 1 of 3 | |
| Bruno | first try | first try | |
| Karen | 1 of 4 | first try | Gengar 15 |
| Lance | 0 of 5 | 0 of 5 | Gyarados 11, Aerodactyl 7, Dragonite 7 |

Against Lance the type-matchup set knocked out two or three of his six each
time, though it used 23 potions over the five battles. (Its first run
stalled at Karen on a move to learn after a level-up, a bot gap since
fixed, and Karen and Lance were played again from the save after Bruno.)
The plain bot with this set at Lv. 58, his top level, won 3 of 8. So at the
level a short grind brings, both sets lose every time to Lance, and he is
the one boss the numbers still put out of line. Getting to Lv. 58 before
him is about 170 wild battles on top of the trainers, by `level_curve.py`'s
model with patch 0026. Lance stays as he is: he is meant to be the hardest story boss,
and he is beatable after that longer grind.

Whitney at 1 of 5 is harder than the plain bot's first-try win at the same
level. That was one run, with `STORY_JITTER` changing every battle, so
neither result says much alone; Stantler and Miltank remain her threats.

## The whole story with smart turns

On the v0.9 build with the test harness, from a fresh boot, the bot played the story with smart turns and
the bulky sets at the levels a short grind brings each boss to (falkner_v2 8, bugsy_v2 14, whitney_v2 21,
morty_v2 25, chuck_v2 34, jasmine_v2 32, pryce_v2 37, radio_tower_v2 42, clair_v2 45, elite_four_v2 53). Its potions are six of
what a player would have by then, kept in the bag. The sets change only at the heals before bosses, so two
story fights in between met the last boss's set at that boss's level; for those the run re-levelled the
party first (`STORY_SWAP_<STAGE>=set:level`): the Azalea rival met the Bugsy set at 18 and Petrel in the
Rocket Hideout the Pryce set at 36, each one under the opponent's average. It played through to Lance,
346 battles and 324 won. Records: run label `full-story-smart` (League fights carry the team's `level`).

| Fight | Team's level | Result | Took the most of ours |
|---|---|---|---|
| Falkner, Proton (Slowpoke Well), Bugsy | 8, 14, 14 | each first try | |
| Rival, Azalea | 18 | first try | |
| Whitney | 21 | first try | |
| Rival, Burned Tower | 25 | second try | Sneasel, Golbat, Misdreavus |
| Morty | 25 | second try | Gengar |
| Chuck | 32 | 0 of 5 | Heracross, Poliwrath |
| Chuck | 34 | first try | |
| Jasmine | 32 | first try | |
| Petrel, Rocket Hideout | 32 (the Jasmine set) | 0 of 5 | Raticate 11, Weezing 9, Golbat 7 |
| Petrel, Rocket Hideout | 36 | first try | |
| Pryce | 37 | third try | Mamoswine, Jynx |
| Radio Tower: rival, Petrel, Proton, Ariana, Archer | 42 | each first try | |
| Clair | 45 | first try | |
| Rival, Victory Road | 53 | first try | |
| Will | 53 | first try | |
| Koga | 53 | second try | Muk, Crobat |
| Bruno | 53 | 0 of 5 | Hitmonlee, Annihilape |
| Bruno | 55 | second try | Annihilape, Machamp |
| Karen | 55 | second try | Houndoom |
| Lance | 55 | 0 of 5 | Dragonite 13, Gyarados 10, Aerodactyl 4 |

**A player who heals and grinds a little should get through Johto.** Every gym fell at the levels the model
gives after a short grind, Chuck at 34, his top level, rather than 32. Two places stand out:

- **Chuck** beat the bot all five times at 32 and lost on the first try at 34. His Heracross and Poliwrath are the hardest pair in mid-Johto
  for these sets; a player wants Flying or Psychic for them, or two more levels.
- **Petrel in the Rocket Hideout** won every time against a team at the last gym's level: his team (36-39) is
  four to seven over Jasmine's set at 32. A player coming from Jasmine meets him well under, with only the
  Lake of Rage and Route 43 to grind on. One under his average, he fell first try.

Both stay as they are: a little levelling gets past each, and that is what a player would do.

**The League goes as it did when played on its own, except Bruno.** Will and Koga fell at 53, as before.
Bruno, a first-try win at 53 when the League was played alone, won all five here: his Hitmonlee and
Annihilape swept the set each time, and the bot spent 15 potions over the five. That earlier win came before
the bot's potion stocking was fixed (see below), which may have affected it, so this result is the one to
go by. His team is Lv. 51-53, so the set lost five times at his top level. Two levels over it, at 55
(Pupitar has evolved into Tyranitar there), he fell on the second try. Karen then fell on the second, and
Lance won all five at 55, as he did at 53, with Dragonite and Gyarados taking most of the team.

So Bruno is the hardest of the four for this set, harder than Chuck: Chuck fell at his own top level,
Bruno only two over his. Hitmonlee (Focus Sash, Swords Dance) and Annihilape (Fighting and Ghost, so Slowbro
resists only half of it) are why; a player would bring Psychic or Flying for them. Lance is still the one
boss well out of reach after a short grind; that was decided earlier, and he stays as he is.

The first try at the League stopped before Victory Road: a current at Tohjo Falls pushed the player back,
and the bot tried the same move forever. The bot now walls off a move that keeps putting it back where it
was, and slides down waterfalls by surfing into them.

Bot gaps found and fixed on the way: room for the Mystery Egg with a party of six; party writes that came out
scrambled (a Bad Egg in battle); potions stocked only in the game's own bag (an earlier search through memory
was writing to anything shaped like a bag slot, and corrupted memory); Cianwood's sand read as a message box;
a screen fading to white during a scene; KOs logged from a battle's memory after it was let go.

## Something else found

In `guide/BOSSES.md`, a few rows were broken: the item, moves and nature ran
together. The guide's report writer gave the item 14 characters, and Never
Melt Ice has 15. That is fixed, and the tables regenerated.
