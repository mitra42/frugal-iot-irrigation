"""Write esp32_io_board/irrigation.kicad_sym: custom rail power symbols + module + FS8205A."""
import os, re, sys, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import dumps, Str
import customsyms
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'esp32_io_board', 'irrigation.kicad_sym')
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
for name in ('VSYS', 'VBAT', '+3V3_SW', '+5V_SW'):
    blocks.append(tmpl.replace('"+3V3"', f'"{name}"').replace('"+3V3_0_1"', f'"{name}_0_1"')
                  .replace('"+3V3_1_1"', f'"{name}_1_1"').replace('\\"+3V3\\"', f'\\"{name}\\"'))
def plain(sym, name):
    s = copy.deepcopy(sym); s[1] = Str(name)
    return '\t' + dumps(s, 1)
mod, _ = customsyms.module_symbol()
blocks.append(plain(mod, 'ESP32-C3-C6-MINI-1U'))
# FS8205A as a 2-unit part, each unit a standard N-MOSFET (graphics from KiCad's 2N7002)
from libload import flat_symbol
from customsyms import _prop, _pin
nm = flat_symbol('Transistor_FET', '2N7002')
gfx = [c for c in nm if isinstance(c, list) and c and c[0] == 'symbol' and str(c[1]).endswith('_0_1')][0]
gfx = copy.deepcopy(gfx); gfx[1] = Str('FS8205A_0_1')
def unit(n, g, s, d):
    return ['symbol', Str(f'FS8205A_{n}_1'),
            _pin(g, 'G', 'input', -5.08, 0, 0), _pin(s, 'S', 'passive', 2.54, -5.08, 90),
            _pin(d, 'D', 'passive', 2.54, 5.08, 270)]
fs = ['symbol', Str('FS8205A'), ['pin_numbers', ['hide', 'yes']], ['pin_names', ['hide', 'yes']],
      ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'], ['in_pos_files', 'yes'],
      ['duplicate_pin_numbers_are_jumpers', 'no'],
      _prop('Reference', 'Q', 5.08, 1.27), _prop('Value', 'FS8205A', 5.08, -1.27),
      _prop('Footprint', 'Package_TO_SOT_SMD:SOT-23-6', 0, 0, True),
      _prop('Datasheet', '~', 0, 0, True),
      _prop('Description', 'Dual N-MOSFET SOT-23-6 (Fuxinsemi), common drain pins 2+5, for 1-cell Li-ion protection with DW01A. Unit A: G1=6 S1=1, unit B: G2=4 S2=3', 0, 0, True),
      gfx, unit(1, '6', '1', '2'), unit(2, '4', '3', '5')]
blocks.append('\t' + dumps(fs, 1))
out = '(kicad_symbol_lib\n\t(version 20251024)\n\t(generator "kicad_symbol_editor")\n\t(generator_version "10.0")\n' + '\n'.join(blocks) + '\n)\n'
open(OUT, 'w').write(out)
print('wrote', OUT, len(out))
