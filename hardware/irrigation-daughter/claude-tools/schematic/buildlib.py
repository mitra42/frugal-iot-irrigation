"""Write daughter/irrigation.kicad_sym: the +3V3_SW rail symbol (the only non-stock symbol on this board)."""
import os, re, sys, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import dumps, Str
import customsyms
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'daughter', 'irrigation.kicad_sym')
t = open(os.path.join(os.environ.get('KICAD10_SYMBOL_DIR', '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols'), 'power.kicad_sym')).read()
m = re.search(r'\n\t\(symbol "\+3V3"\n', t); i = m.start() + 1
d = 0; j = i; ins = False
while True:
    c = t[j]
    if ins:
        if c == '\\': j += 2; continue
        if c == '"': ins = False
    elif c == '"': ins = True
    elif c == '(': d += 1
    elif c == ')':
        d -= 1
        if d == 0: break
    j += 1
tmpl = t[i:j + 1]
blocks = []
# +3V3_SW: the host's switched sensor rail, which is all this board gets for its logic (D3)
for name in ('+3V3_SW',):
    blocks.append(tmpl.replace('"+3V3"', f'"{name}"').replace('"+3V3_0_1"', f'"{name}_0_1"')
                  .replace('"+3V3_1_1"', f'"{name}_1_1"').replace('\\"+3V3\\"', f'\\"{name}\\"'))
out = '(kicad_symbol_lib\n\t(version 20251024)\n\t(generator "kicad_symbol_editor")\n\t(generator_version "10.0")\n' + '\n'.join(blocks) + '\n)\n'
open(OUT, 'w').write(out)
print('wrote', OUT, len(out))
