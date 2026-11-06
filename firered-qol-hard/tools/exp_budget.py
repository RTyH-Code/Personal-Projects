#!/usr/bin/env python3
"""Exp budget vs level caps.

For each stretch of the game between level caps, add up the Exp that the
trainers on those maps give (one-time battles, Gym Leaders included; their
Exp is awarded before the badge, so it's still clamped at the old cap) and work out what level a team would
reach on trainer Exp alone, starting at the previous cap.

usage: python3 tools/hack/exp_budget.py [team sizes, default 3 4 6]
"""
import glob, os, re, sys

R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(R)

# --- species data -----------------------------------------------------------
info = open('src/data/pokemon/species_info.h').read()
yield_, growth = {}, {}
for m in re.finditer(r'\[(SPECIES_\w+)\]\s*=\s*\{(.*?)\n    \}', info, re.S):
    b = m.group(2)
    y = re.search(r'\.expYield\s*=\s*(\d+)', b)
    g = re.search(r'\.growthRate\s*=\s*(GROWTH_\w+)', b)
    if y: yield_[m.group(1)] = int(y.group(1))
    if g: growth[m.group(1)] = g.group(1)
# aliases like #define SPECIES_X SPECIES_OLD_UNOWN_Y
for a, b in re.findall(r'#define (SPECIES_\w+)\s+(SPECIES_OLD_UNOWN_\w+)', open('include/constants/species.h').read()):
    if b in yield_: yield_[a] = yield_[b]

# --- trainer parties ----------------------------------------------------------
tp = open('src/data/trainer_parties.h').read()
parties = {}
for m in re.finditer(r'(sParty_\w+)\[\] = \{(.*?)\n\};', tp, re.S):
    mons = re.findall(r'\.lvl = (\d+),.*?\.species = (SPECIES_\w+)', m.group(2), re.S)
    parties[m.group(1)] = [(int(l), s) for l, s in mons]
tr = open('src/data/trainers.h').read()
trainer_party = dict(re.findall(r'\[(TRAINER_\w+)\] = \{.*?\.party = \w+\((sParty_\w+)\)', tr, re.S))

# --- which maps each trainer is fought on -------------------------------------
trainer_map = {}
for f in glob.glob('data/maps/*/scripts.inc'):
    mp = f.split('/')[2]
    for t in re.findall(r'trainerbattle\w*\s+(TRAINER_\w+)', open(f).read()):
        trainer_map.setdefault(t, mp)

# Map-name prefixes for each stretch, in story order.
SEGMENTS = [
    ('Brock',      16, 5,  ['PalletTown', 'Route1', 'ViridianCity', 'Route22', 'Route2', 'ViridianForest', 'PewterCity']),
    ('Misty',      23, 16, ['Route3', 'MtMoon', 'Route4', 'CeruleanCity', 'Route24', 'Route25']),
    ('Lt. Surge',  28, 23, ['Route5', 'Route6', 'UndergroundPath', 'VermilionCity', 'SSAnne', 'Route11', 'DiglettsCave']),
    ('Erika',      35, 28, ['Route9', 'Route10', 'RockTunnel', 'LavenderTown', 'Route8', 'Route7', 'CeladonCity']),
    ('Koga',       45, 35, ['RocketHideout', 'PokemonTower', 'Route12', 'Route13', 'Route14', 'Route15',
                            'Route16', 'Route17', 'Route18', 'FuchsiaCity', 'SafariZone']),
    ('Sabrina',    47, 45, ['SilphCo', 'SaffronCity']),
    ('Blaine',     51, 47, ['Route19', 'Route20', 'Route21', 'SeafoamIslands', 'CinnabarIsland', 'PokemonMansion']),
    ('Giovanni',   54, 51, ['OneIsland', 'TwoIsland', 'ThreeIsland', 'MtEmber', 'ViridianCity']),
    ('Elite Four', 72, 54, ['Route23', 'VictoryRoad', 'IndigoPlateau', 'Route22']),
]

LEADERS = {'BROCK': 'Brock', 'MISTY': 'Misty', 'LT_SURGE': 'Lt. Surge', 'ERIKA': 'Erika', 'KOGA': 'Koga',
           'SABRINA': 'Sabrina', 'BLAINE': 'Blaine', 'GIOVANNI': 'Giovanni'}

def segment_of(t, mp):
    if t.startswith('TRAINER_LEADER_'): return LEADERS.get(t[len('TRAINER_LEADER_'):])
    if t.startswith('TRAINER_RIVAL_ROUTE22_LATE'): return 'Elite Four'
    if t.startswith('TRAINER_RIVAL_ROUTE22_EARLY'): return 'Brock'
    if mp.startswith('ViridianCity_Gym'): return 'Giovanni'
    for name, _, _, pref in SEGMENTS:
        if any(mp == p or mp.startswith(p + '_') for p in pref):
            return name
    return None

def exp_for(lvl, rate):
    n = lvl
    if rate == 'GROWTH_MEDIUM_SLOW': return int(6 * n**3 / 5 - 15 * n**2 + 100 * n - 140)
    if rate == 'GROWTH_FAST': return 4 * n**3 // 5
    if rate == 'GROWTH_SLOW': return 5 * n**3 // 4
    return n**3

def level_after(start, exp, rate):
    e = exp_for(start, rate) + exp
    lv = start
    while lv < 100 and exp_for(lv + 1, rate) <= e:
        lv += 1
    return lv, e - exp_for(lv, rate)

def gain(b, L, Lp, n):
    """Exp one of n team members gets for a trainer's Lv. L Pokémon (modern formula)."""
    base = b * L // 5 // n
    return int(base * ((2 * L + 10) / (L + Lp + 10)) ** 2.5 + 1) * 3 // 2

def level_of(e, rate):
    l = 1
    while l < 100 and exp_for(l + 1, rate) <= e:
        l += 1
    return l

mons = {s[0]: [] for s in SEGMENTS}
counts = {s[0]: 0 for s in SEGMENTS}
unplaced = []
for t, mp in sorted(trainer_map.items()):
    if t.startswith(('TRAINER_ELITE_FOUR_', 'TRAINER_CHAMPION_')):
        continue
    # Rival battles exist once per starter choice: count one of them.
    if t.startswith('TRAINER_RIVAL') and not t.endswith('SQUIRTLE'):
        continue
    seg = segment_of(t, mp)
    if seg is None:
        unplaced.append((t, mp)); continue
    mons[seg] += parties.get(trainer_party.get(t), [])
    counts[seg] += 1

sizes = [int(a) for a in sys.argv[1:]] or [3, 4, 6]
RATES = [('MF', 'GROWTH_MEDIUM_FAST'), ('MS', 'GROWTH_MEDIUM_SLOW')]
# Carry the team forward: start at Lv. 5, beat each stretch's trainers in turn
# (Exp split evenly, scaled by the team's level at the time), and stop at the
# cap the way the game does.
exp = {(n, r): exp_for(5, r) for n in sizes for _, r in RATES}
print(f"{'Next':<11}{'Cap':>4}{'Trainers':>9}   " + '   '.join(f'{n} mons MF/MS' for n in sizes))
for name, cap, _, _ in SEGMENTS:
    cells = []
    for n in sizes:
        lv = []
        for _, r in RATES:
            e = exp[(n, r)]
            for L, sp in mons[name]:
                e = min(e + gain(yield_.get(sp, 0), L, level_of(e, r), n), exp_for(cap, r))
            exp[(n, r)] = e
            lv.append(level_of(e, r))
        cells.append(f'{lv[0]:>5}/{lv[1]:<6}  ')
    print(f'{name:<11}{cap:>4}{counts[name]:>9}   ' + '   '.join(cells))
print('\nTeam level after each stretch on trainer Exp alone (no wild battles; Gym')
print('Leader Exp included), split evenly, using the modern Exp formula, clamped at')
print('each cap. MF = Medium Fast growth, MS = Medium Slow (the starters and many others).')
if unplaced:
    print('\nNot counted (post-game or unmapped):', ', '.join(sorted({m.split('_')[0] for _, m in unplaced})))
