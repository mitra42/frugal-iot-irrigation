"""Quick placement preview (no KiCad): courtyards coloured by schematic block, refs, ratsnest. -> out/preview.png"""
import json, math, sys, xml.etree.ElementTree as ET
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
FP = json.load(open('fp.json')); PL = json.load(open('placement.json')); BLK = json.load(open('blocks.json'))
W, H = PL['W'], PL['H']; P = PL['place']
def rot_pt(x, y, r):
    a = math.radians(r); c, s = round(math.cos(a), 9), round(math.sin(a), 9); return x * c + y * s, -x * s + y * c
def rect_of(ref):
    x, y, r = P[ref]; b = FP[ref]['bbox']
    pts = [rot_pt(px, py, r) for px in (b[0], b[2]) for py in (b[1], b[3])]
    return min(x + p[0] for p in pts), min(y + p[1] for p in pts), max(x + p[0] for p in pts), max(y + p[1] for p in pts)
def pads_of(ref):
    x, y, r = P[ref]; return {k: (x + rot_pt(*v, r)[0], y + rot_pt(*v, r)[1]) for k, v in FP[ref]['pads'].items()}
COL = dict(usb='#1f77b4', v12='#d62728', chg='#ff7f0e', pwr='#9467bd', mcu='#2ca02c', uio='#17becf',
           i2c='#8c564b', rs485='#e377c2', rly='#7f7f7f')
fig, ax = plt.subplots(figsize=(13, 13 * H / W))
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5, color='k'))
for hx, hy in PL['holes'].values(): ax.add_patch(Circle((hx, hy), 3.0, fill=False, color='k'))
for ref in P:
    x0, y0, x1, y1 = rect_of(ref); c = COL.get(BLK.get(ref), 'k')
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=True, alpha=0.18, color=c))
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=0.6, color=c))
    for px, py in pads_of(ref).values(): ax.plot(px, py, '.', ms=1.5, color=c)
    fs = 7 if (x1 - x0) * (y1 - y0) > 40 else 4.5
    ax.text((x0 + x1) / 2, (y0 + y1) / 2, ref, ha='center', va='center', fontsize=fs, color=c, weight='bold')
if '--rats' in sys.argv:
    from collections import defaultdict
    nets = defaultdict(list)
    for n in ET.parse('../schematic/out/netlist.xml').getroot().iter('net'):
        for node in n.iter('node'): nets[n.get('name')].append((node.get('ref'), node.get('pin')))
    allp = {r: pads_of(r) for r in P}
    for net, nodes in nets.items():
        if net in ('GND',): continue
        pts = list({allp[r][p] for r, p in nodes if p in allp[r]})
        inn = [0]; rest = set(range(1, len(pts)))
        while rest:
            d, a, b = min((math.dist(pts[i], pts[j]), i, j) for i in inn for j in rest)
            ax.plot([pts[a][0], pts[b][0]], [pts[a][1], pts[b][1]], lw=0.35, color='#444', alpha=0.6); inn.append(b); rest.remove(b)
for b, c in COL.items(): ax.plot([], [], 's', color=c, label=b)
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.02), ncol=9, fontsize=8, frameon=False)
ax.set_xlim(-2, W + 2); ax.set_ylim(H + 2, -2); ax.set_aspect('equal'); ax.set_xticks(range(0, int(W) + 1, 10)); ax.set_yticks(range(0, int(H) + 1, 10))
ax.grid(alpha=0.15); plt.tight_layout(); plt.savefig('out/preview.png', dpi=110); print('ok')
