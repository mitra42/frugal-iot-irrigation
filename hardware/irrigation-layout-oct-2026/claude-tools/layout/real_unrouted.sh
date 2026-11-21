#!/bin/bash
# Mac: import a .ses into the pre-route board (out/before_import.kicad_pcb), restore the fixed copper, run DRC and
# list the non-GND connections KiCad still sees open. Leaves the result as the working board. Usage: real_unrouted.sh x.ses
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
L="$(cd "$(dirname "$0")" && pwd)"; cd $L
cp out/before_import.kicad_pcb ../../esp32_io_board/esp32_io_board.kicad_pcb; cp "$1" out/routed.ses
$PY import_ses.py 2>&1 | grep -v -e assert -e traits; $PY copper_snap.py restore 2>&1 | grep -v -e assert -e traits
bash drc.sh
python3 - <<'PY'
import json, re, collections
d = json.load(open('out/drc.json')); c = collections.Counter(); rows = []
for v in d['unconnected_items']:
    a, b = v['items'][:2]; n = re.search(r'\[(.*?)\]', a['description']).group(1); c[n] += 1
    if n != 'GND': rows.append(f"  {n:14} {a['description'][:34]:34} ({a['pos']['x']-50:.1f},{a['pos']['y']-50:.1f}) - {b['description'][:30]} ({b['pos']['x']-50:.1f},{b['pos']['y']-50:.1f})")
print('unconnected', len(d['unconnected_items']), 'non-GND', sum(v for k, v in c.items() if k != 'GND'))
print('\n'.join(rows)); print(collections.Counter(v['type'] for v in d['violations'] if 'silk' not in v['type']).most_common())
PY
