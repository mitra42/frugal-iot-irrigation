"""Placement for the irrigation daughter board (from the irrigation board's place.py). Plain python (no KiCad needed).
Inputs: fp.json (fpmeasure.py), ../schematic/out/netlist.xml. Output: placement.json {ref: [x, y, rot]}, metrics.
Board: W x H mm, origin top-left, y down (KiCad). Rotation in KiCad degrees (CCW on screen).
Eight valve channels along the bottom edge and 12 V input on the left edge beside them, as the irrigation board;
host terminal and OLED header on the top edge; 4x M3 corner holes. Board height is the argument (default 44)."""
import json, math, sys, xml.etree.ElementTree as ET
from collections import defaultdict
W, H = 100.0, float(sys.argv[1]) if len(sys.argv) > 1 else 44.0
FP = json.load(open('fp.json'))
NL = ET.parse('../schematic/out/netlist.xml').getroot()
NETS = defaultdict(list)                      # net -> [(ref, pad)]
for n in NL.iter('net'):
    for node in n.iter('node'): NETS[n.get('name')].append((node.get('ref'), node.get('pin')))
POUR = {'/GND', 'GND'}
HOLE_R = 3.6                                  # M3: 6.0 mm head + margin -> keep parts this far from hole centre
HOLES = {'H1': (4.0, 4.0), 'H2': (W - 4.0, 4.0), 'H3': (4.0, H - 4.0), 'H4': (W - 4.0, H - 4.0)}
GAP = 0.3                                     # courtyard-to-courtyard spacing for packed parts
EDGE = 0.6                                    # courtyard inset from board edge for packed parts

def rot_pt(x, y, r):
    a = math.radians(r); c, s = round(math.cos(a), 9), round(math.sin(a), 9)
    return x * c + y * s, -x * s + y * c
def rect_of(ref, x, y, r):
    b = FP[ref]['bbox']
    pts = [rot_pt(px, py, r) for px in (b[0], b[2]) for py in (b[1], b[3])]
    xs = [x + p[0] for p in pts]; ys = [y + p[1] for p in pts]
    return [min(xs), min(ys), max(xs), max(ys)]
def pads_of(ref, x, y, r):
    return {k: (x + rot_pt(*v, r)[0], y + rot_pt(*v, r)[1]) for k, v in FP[ref]['pads'].items()}

P = {}                                        # ref -> (x, y, rot)
# ---------------- anchors ----------------
# The valve band is the irrigation board's (its D79-D82), unchanged: eight KF128 2-way terminals butted at 10.16 mm
# along the bottom edge, each channel's parts in a column straight above its terminal, so valve_route.py can draw
# the 2 A paths as straight lines:
#   SS34 flyback: cathode (+12V) over pin 1, anode (VALVE) over pin 2
#   4.7k (+12V -> LED_V) left, LED (LED_V -> VALVE) right, its cathode at x = VALVE trunk
#   AO3400A rot 270: drain pointing down at x = VALVE trunk, source top-left (to GND vias), gate top-right
#   100k pull-down above the FET, gate end over the gate pad, GND end over the source pad
# References are the daughter's: channel i (0-7) is J(4+i), Q(1+i), SS34 D(3+2i), LED D(4+2i), 100k R(3+2i),
# 4.7k R(4+2i).
VP = 10.16
VX0 = W / 2 - 4 * VP + 2.54                   # pin 1 of channel 1; row centred on the board
TY = H - 5.45                                 # pin row: courtyard (+-5.45) flush with the bottom edge
yD = TY - 5.45 - 0.25 - 1.79
yR = yD - 1.79 - 0.25 - 0.78
yQ = yR - 0.78 - 0.25 - 1.98
yG = yQ - 1.98 - 0.25 - 0.78
BAND_TOP = yG - 0.78
TRUNK = 5.08 + 0.49                           # VALVE trunk x, relative to pin 1: just right of pin 2's centre
for i in range(8):
    xa = VX0 + i * VP; xt = xa + TRUNK
    P[f'J{4 + i}'] = (xa, TY, 0)
    P[f'D{3 + 2 * i}'] = (xa + 2.54, yD, 0)           # SS34, pad 1 (K) left
    P[f'R{4 + 2 * i}'] = (xa + 0.3, yR, 0)            # 4.7k, pad 1 (+12V) left
    P[f'D{4 + 2 * i}'] = (xt - 0.79, yR, 180)         # LED, pad 2 (A) left, pad 1 (K, VALVE) on the trunk
    P[f'Q{1 + i}'] = (xt, yQ, 270)                    # AO3400A: D (0, +0.94), S (-0.95, -0.94), G (+0.95, -0.94)
    P[f'R{3 + 2 * i}'] = (xt + 0.13, yG, 180)         # 100k: pad 1 (gate) at +0.82, pad 2 (GND) at -0.82
# 12 V input on the left edge just above the valve row, as the irrigation board: J2 pin 1 -> F1 -> D1 (SS54) in a
# line; D1 stands on end so its cathode drops to three vias between channels 1 and 2, where the 2 mm +12V bus on
# B.Cu runs along the terminal row.
YJ = BAND_TOP - 0.6 - 7.62 - 0.3
P['J2'] = (5.45, YJ, 270)
P['F1'] = (14.2, YJ, 0)                              # 1812: pad 1 (12V_IN) left, pad 2 right
P['D1'] = (19.1, YJ + 2.0, 90)                       # SS54 on end: anode (pad 2) top on F1's line, cathode below
P['C1'] = (14.5, BAND_TOP - 2.3, 180)                # +12V bulk at the feed: pad 1 (+12V) right, towards the vias
FEED = [(19.9, BAND_TOP - 2.4), (21.0, BAND_TOP - 2.4), (22.1, BAND_TOP - 2.4)]   # +12V vias to the bus
# Host terminal and OLED header on the top edge (D6). J1 rot 180 so the wire entry faces the top edge (pin 1 is
# then the rightmost); J3 rot 90, pins running +x from pin 1.
P['J1'] = (36.0, 4.4, 180)
P['J3'] = (62.0, 2.6, 90)
# The 12 V sense divider just right of J1, beside its V12 pin (pin 1, the rightmost): left to the placer it went
# under J1, where pinlabels.py writes the pin names.
P['R1'] = (40.2, 3.2, 90)
P['R2'] = (40.2, 6.8, 90)
# I2C pull-ups (D12) beside them, between J1 and J3 where SDA, SCL and 3V3_SW already run along the top
P['R19'] = (45.0, 3.0, 90)
P['R20'] = (47.5, 3.0, 90)
# TCA9534 centred above the valve row: P0-P3 (pins 4-7) on its left face channels 1-4, P4-P7 (pins 9-12) 5-8.
P['U1'] = (W / 2, BAND_TOP - 5.0, 0)
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'schematic'))
import circuit
BLK = {}; _n = {}
for p in circuit.P:   # references are numbered in circuit.py's order, as dbase.py does
    _n[p['prefix']] = _n.get(p['prefix'], 0) + 1; BLK[f"{p['prefix']}{_n[p['prefix']]}"] = p['block']
MID_BOT = BAND_TOP - 1.0                      # above is the input, host and expander; below the gate lines and valves
REGION = {   # x0, y0, x1, y1 -- a packed part's courtyard must lie inside its block's region
    'v12':  (11.0, 6.0, 40.0, MID_BOT),
    'host': (11.0, 0.6, 70.0, MID_BOT),
    'oled': (50.0, 0.6, 90.0, 10.0),
    'rly':  (11.0, 6.0, 90.0, MID_BOT),
}
NEAR = {'D2': ('D1', '1'), 'C2': ('U1', '16')}
NEAR_W = 6.0
ORDER = ['v12', 'host', 'oled', 'rly']
FIXED = set(P)
RESERVED = [[VX0 - 2.54 - 0.3, BAND_TOP - 0.3, VX0 + 7 * VP + 7.62 + 0.3, H],   # valve band
            [19.2, BAND_TOP - 3.6, 22.8, BAND_TOP]]                            # +12V feed vias
GAP = 0.5
def free(rr, placed_rects, region):
    if rr[0] < max(EDGE, region[0]) or rr[1] < max(EDGE, region[1]) or rr[2] > min(W - EDGE, region[2]) \
            or rr[3] > min(H - EDGE, region[3]): return False
    if any(not (rr[2] <= q[0] or q[2] <= rr[0] or rr[3] <= q[1] or q[3] <= rr[1]) for q in RESERVED): return False
    for hx, hy in HOLES.values():
        cx = min(max(hx, rr[0]), rr[2]); cy = min(max(hy, rr[1]), rr[3])
        if math.hypot(cx - hx, cy - hy) < HOLE_R: return False
    for q in placed_rects:
        if rr[0] < q[2] + GAP and q[0] < rr[2] + GAP and rr[1] < q[3] + GAP and q[1] < rr[3] + GAP: return False
    return True
rects = {r: rect_of(r, *P[r]) for r in P}
def partners(ref):
    out = []
    for net, nodes in NETS.items():
        if net in POUR: continue
        mine = [p for r, p in nodes if r == ref]
        if not mine: continue
        w = 1.0 / max(1, len(nodes) - 1)
        for r, p in nodes:
            if r != ref and r in P: out.append((mine, pads_of(r, *P[r])[p], w))
    return out
def cost(ref, x, y, r, prt):
    pads = pads_of(ref, x, y, r)
    c = sum(w * min(math.dist(pads[m], q) for m in mine if m in pads) for mine, q, w in prt)
    if ref in NEAR and NEAR[ref][0] in P:
        q = pads_of(NEAR[ref][0], *P[NEAR[ref][0]])[NEAR[ref][1]]
        c += NEAR_W * min(math.dist(v, q) for v in pads.values())
    return c
area = lambda r: (FP[r]['bbox'][2] - FP[r]['bbox'][0]) * (FP[r]['bbox'][3] - FP[r]['bbox'][1])
def place_one(ref, region):
    prt = partners(ref)
    if ref in NEAR and NEAR[ref][0] in P:
        tx, ty = pads_of(NEAR[ref][0], *P[NEAR[ref][0]])[NEAR[ref][1]]
    elif prt:
        tw = sum(w for _, _, w in prt)
        tx = sum(q[0] * w for _, q, w in prt) / tw; ty = sum(q[1] * w for _, q, w in prt) / tw
    else:
        tx, ty = (region[0] + region[2]) / 2, (region[1] + region[3]) / 2
    tx = min(max(tx, region[0]), region[2]); ty = min(max(ty, region[1]), region[3])
    cands = []; first = None; step = 0.25
    for ring in range(0, 600):
        rad = ring * step
        if first is not None and rad > first + 3.0: break
        n = max(1, int(2 * math.pi * rad / step))
        for k in range(n):
            a = 2 * math.pi * k / n
            x = round((tx + rad * math.cos(a)) / 0.05) * 0.05; y = round((ty + rad * math.sin(a)) / 0.05) * 0.05
            for r in (0, 90, 180, 270):
                rr = rect_of(ref, x, y, r)
                if free(rr, rects.values(), region):
                    cands.append((cost(ref, x, y, r, prt), x, y, r))
                    if first is None: first = rad
    if not cands: return False
    c, x, y, r = min(cands)
    P[ref] = (x, y, r); rects[ref] = rect_of(ref, x, y, r); return True
for b in ORDER:
    todo = [r for r in FP if BLK.get(r) == b and r not in P]
    while todo:
        ready = [r for r in todo if r not in NEAR or NEAR[r][0] in P] or todo
        best = max(ready, key=lambda r: (round(sum(w for _, _, w in partners(r)), 3), area(r)))
        reg = list(REGION[b]); grow = 0
        while not place_one(best, reg):
            grow += 1; reg = [reg[0] - 1, reg[1] - 1, reg[2] + 1, reg[3] + 1]
            if grow > 30: sys.exit(f'cannot place {best} in {b}')
        if grow: print(f'  {best} ({b}) needed region +{grow} mm')
        todo.remove(best)
# Hand-placed anchors are not checked by free(), only packed parts are; check every pair here so an anchor
# that lands on another (C5 on U2, the first time). 0.1 mm tolerance: the butted KF128s touch, and the measured
# courtyard box is ~0.05 mm bigger each side than the drawn line fails the placement rather than surfacing in DRC after routing.
ov = [(a, c) for i, a in enumerate(P) for c in list(P)[i + 1:]
      if (lambda p, q: p[0] < q[2] - 0.1 and q[0] < p[2] - 0.1 and p[1] < q[3] - 0.1 and q[1] < p[3] - 0.1)(rects.get(a) or rect_of(a, *P[a]), rects.get(c) or rect_of(c, *P[c]))]
if ov: sys.exit(f'courtyards overlap: {ov}')
# and the same for the mounting holes, which free() checks only for packed parts: below 44 mm J2 lands on H1
oh = [(r, h) for r in P for h, (hx, hy) in HOLES.items()
      if (lambda q: math.hypot(min(max(hx, q[0]), q[2]) - hx, min(max(hy, q[1]), q[3]) - hy))(rects.get(r) or rect_of(r, *P[r])) < HOLE_R]
if oh: sys.exit(f'parts on mounting holes: {oh}')
# ---------------- metrics ----------------
def mst(pts):
    if len(pts) < 2: return [], 0.0
    inn = [0]; edges = []; tot = 0.0
    rest = set(range(1, len(pts)))
    while rest:
        d, a, b = min((math.dist(pts[i], pts[j]), i, j) for i in inn for j in rest)
        edges.append((pts[a], pts[b])); tot += d; inn.append(b); rest.remove(b)
    return edges, tot
def cross(e, f):
    (a, b), (c, d) = e, f
    if len({a, b, c, d}) < 4: return False
    o = lambda p, q, r: (q[0]-p[0])*(r[1]-p[1]) - (q[1]-p[1])*(r[0]-p[0])
    return (o(a, b, c) * o(a, b, d) < 0) and (o(c, d, a) * o(c, d, b) < 0)
allpads = {r: pads_of(r, *P[r]) for r in P}
E = []; L = 0.0
for net, nodes in NETS.items():
    if net in POUR: continue
    pts = list({allpads[r][p] for r, p in nodes if p in allpads[r]})
    e, t = mst(pts); L += t; E += [(net, x) for x in e]
X = sum(1 for i in range(len(E)) for j in range(i + 1, len(E)) if E[i][0] != E[j][0] and cross(E[i][1], E[j][1]))
json.dump(dict(W=W, H=H, holes=HOLES, band_top=BAND_TOP, feed=FEED, place={r: [round(v[0], 3), round(v[1], 3), v[2]] for r, v in P.items()}),
          open('placement.json', 'w'), indent=0)
print(f'board {W} x {H}: placed {len(P)}; ratsnest {L:.0f} mm excl. GND; crossings {X}')
