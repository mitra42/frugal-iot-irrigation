import json, sys
from collections import Counter
d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'out/drc.json'))
SILK = ('silk_overlap', 'silk_over_copper', 'silk_edge_clearance', 'text_height', 'text_thickness')
for sec in ('violations', 'unconnected_items', 'schematic_parity'):
    L = d.get(sec, []); c = Counter(v['type'] for v in L); print(sec, len(L), dict(c.most_common(12)))
for v in d.get('violations', []) + d.get('schematic_parity', []):
    if v['type'] not in SILK: print('  ', v['type'], v['description'][:70], [i['description'][:55] for i in v['items']][:2])
