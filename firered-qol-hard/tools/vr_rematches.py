#!/usr/bin/env python3
"""Victory Road VS Seeker rematches.

Gives every Victory Road trainer a stronger rematch team (+LEVEL_BOOST levels,
evolved where the new level allows) in an unused Ruby/Sapphire trainer slot,
and registers it with the VS Seeker. Rematches can be repeated, so Victory
Road becomes a place to train for the Elite Four.

Runs once against the hack's data (after peak_trainers.py); it refuses to run
twice.
"""
import glob, os, re, sys

R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(R)
LEVEL_BOOST = 8
# Unused RS trainer slots (not used by the peak trainers or as hack flags).
SLOTS = ['TRAINER_RS_TUBER_F', 'TRAINER_RS_TUBER_M', 'TRAINER_KINDLER', 'TRAINER_RS_CAMPER',
         'TRAINER_BUG_MANIAC', 'TRAINER_RS_PSYCHIC_M', 'TRAINER_RS_PSYCHIC_F', 'TRAINER_RS_GENTLEMAN',
         'TRAINER_SCHOOL_KID_M', 'TRAINER_SCHOOL_KID_F', 'TRAINER_SR_AND_JR', 'TRAINER_POKEFAN_M',
         'TRAINER_POKEFAN_F', 'TRAINER_EXPERT_M', 'TRAINER_EXPERT_F', 'TRAINER_RS_YOUNGSTER']
# Stone or item evolutions a trainer would have used by now.
STONE = {'VULPIX': 'NINETALES', 'CLEFAIRY': 'CLEFABLE', 'JIGGLYPUFF': 'WIGGLYTUFF',
         'WEEPINBELL': 'VICTREEBEL', 'POLIWHIRL': 'POLIWRATH', 'GROWLITHE': 'ARCANINE',
         'EXEGGCUTE': 'EXEGGUTOR', 'SHELLDER': 'CLOYSTER', 'STARYU': 'STARMIE'}


def read(p):
    return open(p).read()


def write(p, s):
    open(p, 'w').write(s)


op = read('include/constants/opponents.h')
if 'TRAINER_HACK_VR_' in op:
    sys.exit('Victory Road rematches are already in place.')

evo = read('src/data/pokemon/evolution.h')
level_evo = {}
for sp, body in re.findall(r'\[SPECIES_(\w+)\]\s*=\s*\{(.*?)\}\}', evo):
    for method, param, target in re.findall(r'\{?(EVO_LEVEL\w*),\s*(\d+),\s*SPECIES_(\w+)', body):
        if method != 'EVO_LEVEL_SHEDINJA':
            level_evo.setdefault(sp, (int(param), target))


def evolve(sp, lvl):
    for _ in range(3):
        if sp in level_evo and level_evo[sp][0] <= lvl:
            sp = level_evo[sp][1]
        elif sp in STONE:
            sp = STONE[sp]
        else:
            break
    return sp


# Victory Road trainers, in map order.
trainers = []
for f in sorted(glob.glob('data/maps/VictoryRoad_*/scripts.inc')):
    mp = f.split('/')[2]
    const = 'MAP_' + re.sub(r'(?<=[a-z])(?=[A-Z0-9])', '_', mp).upper()
    for t in re.findall(r'trainerbattle\w*\s+(TRAINER_\w+)', read(f)):
        if (t, const) not in trainers:
            trainers.append((t, const))
assert len(trainers) <= len(SLOTS), len(trainers)

tr = read('src/data/trainers.h')
tp = read('src/data/trainer_parties.h')
vs = read('src/vs_seeker.c')
defines, parties, rows = [], [], []
for (t, mapconst), slot in zip(trainers, SLOTS):
    name = t[len('TRAINER_'):]
    new = 'TRAINER_HACK_VR_' + name
    entry = re.search(r'    \[' + t + r'\] = \{\n(.*?)\n    \},\n', tr, re.S).group(1)
    macro, party = re.search(r'\.party = (\w+)\((sParty_\w+)\)', entry).groups()
    m = re.search(r'static const struct (\w+) ' + party + r'\[\] = \{\n(.*?)\n\};\n', tp, re.S)
    stype, body = m.groups()

    # Evolve each Pokémon its new level allows, unless the team already has
    # what it would become (keeps the team varied).
    team = re.findall(r'\.species = SPECIES_(\w+)', body)

    def bump(mon):
        lvl = int(re.search(r'\.lvl = (\d+)', mon).group(1)) + LEVEL_BOOST
        sp = re.search(r'\.species = SPECIES_(\w+)', mon).group(1)
        to = evolve(sp, lvl)
        if to != sp and to not in team:
            team[team.index(sp)] = to
            sp = to
        mon = re.sub(r'\.lvl = \d+', f'.lvl = {lvl}', mon)
        return re.sub(r'\.species = SPECIES_\w+', f'.species = SPECIES_{sp}', mon)

    body = re.sub(r'    \{\n.*?\n    \}', lambda x: bump(x.group(0)), body, flags=re.S)
    newparty = party + 'VR'
    parties.append(f'static const struct {stype} {newparty}[] = {{\n{body}\n}};\n')
    newentry = entry.replace(f'{macro}({party})', f'{macro}({newparty})')
    tr = re.sub(r'    \[' + slot + r'\] = \{\n.*?\n    \},\n',
                lambda _: f'    [{slot}] = {{ // FireRed QoL+Hard: {name} Victory Road rematch\n{newentry}\n    }},\n',
                tr, count=1, flags=re.S)
    defines.append(f'#define {new:<40} {slot}')
    rows.append(f'   {{ {{{t}, {new}}},\n      MAP({mapconst}) }},')

block = '// FireRed QoL+Hard: Victory Road VS Seeker rematches (tools/hack/vr_rematches.py)\n' + '\n'.join(defines) + '\n\n'
k = op.rindex('#endif')
write('include/constants/opponents.h', op[:k] + block + op[k:])
tp = tp.rstrip('\n') + '\n\n// FireRed QoL+Hard: Victory Road rematch teams\n' + '\n'.join(parties)
write('src/data/trainer_parties.h', tp)
write('src/data/trainers.h', tr)
start = vs.index('static const struct RematchData sRematches[] = {')
end = vs.index('\n};', start)
vs = vs[:end] + '\n   // FireRed QoL+Hard: Victory Road rematches\n' + '\n'.join(rows) + vs[end:]
write('src/vs_seeker.c', vs)
# Trainer scripts: offer the rematch when the VS Seeker has flagged the trainer.
for f in sorted(glob.glob('data/maps/VictoryRoad_*/scripts.inc')):
    sc = read(f)

    def add(m):
        label, kind, args, post = m.group(1), m.group(2), m.group(3), m.group(4)
        rematch = 'trainerbattle_rematch_double' if kind == 'double' else 'trainerbattle_rematch'
        return (f'{label}::\n\ttrainerbattle_{kind} {args}\n'
                f'\tspecialvar VAR_RESULT, ShouldTryRematchBattle\n'
                f'\tgoto_if_eq VAR_RESULT, TRUE, {label}Rematch\n'
                f'\tmsgbox {post}, MSGBOX_AUTOCLOSE\n\tend\n\n'
                f'{label}Rematch::\n\t{rematch} {args}\n'
                f'\tmsgbox {post}, MSGBOX_AUTOCLOSE\n\tend\n')
    sc = re.sub(r'(\w+)::\n\ttrainerbattle_(single|double) (TRAINER_\w+[^\n]*)\n\tmsgbox (\w+), MSGBOX_AUTOCLOSE\n\tend\n', add, sc)
    write(f, sc)
print(f'{len(trainers)} Victory Road rematches added.')
