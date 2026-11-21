"""Write esp32_io_board/irrigation.kicad_sym: custom rail power symbols + module + XB5353A."""
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
# XB5353A (XySemi, C80628): one-cell Li-ion protection with integrated MOSFETs, SOT-23-5 (D87). Same symbol as
# frugal-iot-hw-lora. Pins per datasheet: 1 VT (test, leave open), 2 GND (cell -), 3 VDD (cell +), 4/5 VM (pack -).
# It replaced DW01A + FS8205A; the FS8205A's two-unit symbol (D36) went with it.
from customsyms import _prop, _pin, _sym, _rect
pins = [_pin('3', 'VDD', 'power_in', -7.62, 2.54, 0), _pin('2', 'GND', 'passive', -7.62, -2.54, 0),
        _pin('4', 'VM', 'passive', 7.62, 2.54, 180), _pin('5', 'VM', 'passive', 7.62, -2.54, 180),
        _pin('1', 'VT', 'passive', 2.54, 7.62, 270)]
props = [_prop('Reference', 'U', 0, 7.62 + 1.27), _prop('Value', 'XB5353A', 0, -6.35),
         _prop('Footprint', 'Package_TO_SOT_SMD:SOT-23-5', 0, 0, True), _prop('Datasheet', '~', 0, 0, True),
         _prop('Description', 'XySemi XB5353A one-cell Li-ion protection IC with integrated MOSFETs (3 A discharge OC, 4.30/2.4 V), SOT-23-5', 0, 0, True)]
blocks.append('\t' + dumps(_sym('XB5353A', props, _rect(-5.08, -5.08, 5.08, 5.08), pins), 1))
out = '(kicad_symbol_lib\n\t(version 20251024)\n\t(generator "kicad_symbol_editor")\n\t(generator_version "10.0")\n' + '\n'.join(blocks) + '\n)\n'
open(OUT, 'w').write(out)
print('wrote', OUT, len(out))
