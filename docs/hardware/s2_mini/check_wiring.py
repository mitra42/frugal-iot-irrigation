#!/usr/bin/env python3
"""Check that platformio.ini, wiring.md and the schematic all agree about the pins.

Three sources have to say the same thing, and nothing in the normal build catches it when they
drift:

  platformio.ini  [env:s2_mini]        the source of truth (platform.h is generated from it)
  wiring.md       connection table     what somebody with a soldering iron reads
  the schematic   U1's net labels      what the PDF and the BOM come from

Run from anywhere:  python3 docs/hardware/s2_mini/check_wiring.py
Exits non-zero on any disagreement.
"""
import os, re, subprocess, sys, xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
PIO = os.path.join(ROOT, 'platformio.ini')
WIRING = os.path.join(HERE, 'wiring.md')
SCH = os.path.join(HERE, 's2_mini_irrigation.kicad_sch')
CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'

# key -> (platformio flag, expected net label on U1 in the schematic)
SIGNALS = {
    'valve1':   ('OSPIT_VALVE1_PIN',      'VALVE1_GPIO'),
    'valve2':   ('OSPIT_VALVE2_PIN',      'VALVE2_GPIO'),
    'valve3':   ('OSPIT_VALVE3_PIN',      'VALVE3_GPIO'),
    'pump':     ('OSPIT_PUMP_PIN',        'PUMP_GPIO'),
    'load':     ('OSPIT_LOAD_PIN',        'LOAD_GPIO'),
    'tank':     ('OSPIT_TANK_PIN',        'TANK_SENSE'),
    'rs485_rx': ('SYSTEM_RS485_RX_PIN',   'RS485_RX'),
    'rs485_tx': ('SYSTEM_RS485_TX_PIN',   'RS485_TX'),
    'battery':  ('SENSOR_BATTERY_PIN',    'BAT_SENSE'),
}

fail = []

def note(msg):
    fail.append(msg)
    print('MISMATCH: ' + msg)

# ---- 1. platformio.ini, [env:s2_mini] only -----------------------------------------------
text = open(PIO).read()
m = re.search(r'^\[env:s2_mini\](.*?)(?=^\[|\Z)', text, re.S | re.M)
if not m:
    sys.exit('could not find [env:s2_mini] in platformio.ini')
env = m.group(1)
pio = {}
for key, (flag, _) in SIGNALS.items():
    # a commented-out flag does not count
    mm = re.search(rf'^\s*-D\s+{flag}\s*=\s*(\d+)', env, re.M)
    pio[key] = int(mm.group(1)) if mm else None

# ---- 2. wiring.md connection table -------------------------------------------------------
wir = {}
if os.path.exists(WIRING):
    for line in open(WIRING):
        c = [x.strip() for x in line.strip().strip('|').split('|')] if line.strip().startswith('|') else None
        if not c or len(c) < 3 or c[0] in ('Key', ':---', '---'):
            continue
        if c[0] in SIGNALS:
            g = re.match(r'GPIO(\d+)', c[1])
            wir[c[0]] = int(g.group(1)) if g else None
else:
    note('wiring.md not found')

# ---- 3. the schematic, via KiCad's own netlist --------------------------------------------
sch = {}
if os.path.exists(CLI):
    subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadxml',
                    '-o', '/tmp/_cw.xml', SCH], capture_output=True)
    root = ET.parse('/tmp/_cw.xml').getroot()
    # U1 pin number -> GPIO name, from the cached symbol in the netlist
    pinname = {}
    for lib in root.iter('libpart'):
        if lib.get('part') == 'S2_Mini':
            for p in lib.iter('pin'):
                pinname[p.get('num')] = p.get('name')
    netof = {}
    for net in root.find('nets'):
        for n in net.findall('node'):
            if n.get('ref') == 'U1':
                netof[n.get('pin')] = net.get('name').lstrip('/')
    for num, nm in pinname.items():
        g = re.match(r'GPIO(\d+)$', nm or '')
        if g and num in netof:
            sch[netof[num]] = int(g.group(1))
else:
    print('note: kicad-cli not found, skipping the schematic check')
    sch = None

# ---- compare ------------------------------------------------------------------------------
print(f'{"key":<10} {"platformio.ini":>14} {"wiring.md":>10} {"schematic":>10}')
for key, (flag, label) in SIGNALS.items():
    p = pio.get(key)
    w = wir.get(key)
    s = sch.get(label) if sch is not None else None
    print(f'{key:<10} {str(p):>14} {str(w):>10} {str(s):>10}')
    if p is None:
        note(f'{key}: {flag} is not set in [env:s2_mini] - the drawing documents a pin the '
             f'firmware will not use')
        continue
    if w is None:
        note(f'{key}: missing from the wiring.md table')
    elif w != p:
        note(f'{key}: platformio.ini says GPIO{p}, wiring.md says GPIO{w}')
    if sch is not None:
        if s is None:
            note(f'{key}: no U1 pin on net {label} in the schematic')
        elif s != p:
            note(f'{key}: platformio.ini says GPIO{p}, schematic has {label} on GPIO{s}')

print()
if fail:
    print(f'{len(fail)} mismatch(es)')
    sys.exit(1)
print('platformio.ini, wiring.md and the schematic agree on all %d signals' % len(SIGNALS))
