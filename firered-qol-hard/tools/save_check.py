#!/usr/bin/env python3
"""Save compatibility check.

Compares the structures that make up a save file between a git ref (an older
release) and the working tree. Field names are ignored, so renaming an unused
field doesn't count; a change of type, array size, bit width or field order
does. The Pokédex flag arrays depend on NUM_SPECIES, so that's checked too.

usage: python3 tools/hack/save_check.py REF
exit status 0 = saves from REF still load, 1 = the layout changed
"""
import os, re, subprocess, sys

R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FILES = ['include/global.h', 'include/pokemon.h', 'include/pokemon_storage_system.h',
         'include/global.berry.h', 'include/global.fieldmap.h']
STRUCTS = ['SaveBlock1', 'SaveBlock2', 'Pokedex', 'PokemonStorage', 'BoxPokemon', 'Pokemon',
           'PokemonSubstruct0', 'PokemonSubstruct1', 'PokemonSubstruct2', 'PokemonSubstruct3',
           'DaycareMon', 'DayCare', 'Roamer', 'ItemSlot', 'Coords16', 'WarpData', 'Time']


def read(ref, path):
    if ref is None:
        p = os.path.join(R, path)
        return open(p).read() if os.path.exists(p) else ''
    r = subprocess.run(['git', 'show', f'{ref}:{path}'], cwd=R, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ''


def num_species(ref):
    s = read(ref, 'include/constants/species.h')
    m = re.search(r'#define SPECIES_EGG (\d+)', s) or re.search(r'#define NUM_SPECIES (\d+)', s)
    return int(m.group(1)) if m else None


def layout(ref):
    text = '\n'.join(read(ref, f) for f in FILES)
    text = re.sub(r'//[^\n]*|/\*.*?\*/', '', text, flags=re.S)
    out = {}
    for name in STRUCTS:
        m = re.search(r'struct ' + name + r'\s*\{(.*?)\n\};', text, re.S)
        if not m:
            continue
        fields = []
        for decl in m.group(1).split(';'):
            decl = ' '.join(decl.split())
            if not decl:
                continue
            # keep the type, the array sizes and the bit width; drop the name
            t = re.sub(r'\b(\w+)\s*((\[[^\]]*\])*)\s*(:\s*\d+)?$', lambda x: 'NAME' + (x.group(2) or '') + (x.group(4) or ''), decl)
            fields.append(t)
        out[name] = fields
    return out


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    ref = sys.argv[1]
    problems = []
    a, b = num_species(ref), num_species(None)
    if a and b and (a + 7) // 8 != (b + 7) // 8:
        problems.append(f'Pokédex flag arrays changed size: {(a + 7) // 8} -> {(b + 7) // 8} bytes (NUM_SPECIES {a} -> {b})')
    old, new = layout(ref), layout(None)
    for name in STRUCTS:
        if old.get(name) != new.get(name):
            o, n = old.get(name, []), new.get(name, [])
            diff = [f'    - {x}' for x in o if x not in n] + [f'    + {x}' for x in n if x not in o]
            problems.append(f'struct {name} changed:\n' + '\n'.join(diff[:12] or ['    (field order changed)']))
    if problems:
        print(f'Saves from {ref} may NOT load correctly:')
        for p in problems:
            print('  ' + p)
        sys.exit(1)
    print(f'Save layout matches {ref}: saves carry over.')


if __name__ == '__main__':
    main()
