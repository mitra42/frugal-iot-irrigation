"""Placement for the ESP32 I/O board. Plain python (no KiCad needed).
Inputs: fp.json (fpmeasure.py), ../schematic/out/netlist.xml. Output: placement.json {ref: [x, y, rot]}, metrics.
Board: W x H mm, origin top-left, y down (KiCad). Rotation in KiCad degrees (CCW on screen).
Decisions (Mitra, 14 Oct 2026, D49): <=100x100, 4x M3 corner holes, 2 layers, field terminals along the top long
edge, USB-C + LiPo on short edges. Since the relays went (D79-D81): eight valve channels along the bottom edge,
12 V input on the left edge beside them, board height is the argument (default 70)."""
import json, math, sys, xml.etree.ElementTree as ET
from collections import defaultdict
W, H = 100.0, float(sys.argv[1]) if len(sys.argv) > 1 else 70.0
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
# Valve channels along the bottom edge (D79-D82): eight KF128 2-way terminals butted at 10.16 mm (the block width,
# so the row is 81.3 mm and fits between the bottom corner holes). Rot 0: wire entry (+y local) faces the bottom
# edge, pin 1 (+12V) left, pin 2 (VALVEn) right. Each channel's parts sit in a column straight above its terminal,
# placed so that valve_route.py can draw the 2 A paths as straight lines:
#   SS34 flyback: cathode (+12V) over pin 1, anode (VALVE) over pin 2
#   4.7k (+12V -> LED_V) left, LED (LED_V -> VALVE) right, its cathode at x = VALVE trunk
#   AO3400A rot 270: drain pointing down at x = VALVE trunk, source top-left (to GND vias), gate top-right
#   100k pull-down above the FET, gate end over the gate pad, GND end over the source pad
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
    P[f'J{11 + i}'] = (xa, TY, 0)
    P[f'D{10 + 2 * i}'] = (xa + 2.54, yD, 0)          # SS34, pad 1 (K) left
    P[f'R{40 + 2 * i}'] = (xa + 0.3, yR, 0)           # 4.7k, pad 1 (+12V) left
    P[f'D{11 + 2 * i}'] = (xt - 0.79, yR, 180)        # LED, pad 2 (A) left, pad 1 (K, VALVE) on the trunk
    P[f'Q{8 + i}'] = (xt, yQ, 270)                    # AO3400A: D (0, +0.94), S (-0.95, -0.94), G (+0.95, -0.94)
    P[f'R{39 + 2 * i}'] = (xt + 0.13, yG, 180)        # 100k: pad 1 (gate) at +0.82, pad 2 (GND) at -0.82
# 12 V input on the left edge just above the valve row, so the 3 A loop is short: rot 270 puts the wire entry
# facing -x, pin 1 (12V_IN) above pin 2 (GND). J2 pin 1 -> F1 -> D2 in a line; D2 stands on end so its cathode
# drops to three vias between channels 1 and 2, where a 2 mm +12V bus on B.Cu runs along the terminal row (D82).
YJ = BAND_TOP - 0.6 - 7.62 - 0.3
P['J2'] = (5.45, YJ, 270)
P['F1'] = (14.2, YJ, 0)                              # 1812: pad 1 (12V_IN) left, pad 2 right
P['D2'] = (19.1, YJ + 2.0, 90)                       # SS54 on end: anode (pad 2) top on F1's line, cathode below
P['C22'] = (14.5, BAND_TOP - 2.3, 180)               # +12V bulk at the feed: pad 1 (+12V) right, towards the vias
FEED = [(19.9, BAND_TOP - 2.4), (21.0, BAND_TOP - 2.4), (22.1, BAND_TOP - 2.4)]   # +12V vias to the bus
# Top edge terminals: rot 180 so wire entry faces the top edge. Pin 1 is then the rightmost pin.
top = [('J10', 4.4, 9.69), ('J8', 4.4, 9.69), ('J6', 4.4, 4.62), ('J7', 4.4, 4.62)]
x = 9.0
for ref, py, right in top:                    # 'right' = local +x extent; after rot 180 it is the left extent
    left = x + right; P[ref] = (left, py, 180); x = left - FP[ref]['bbox'][0] + 1.0
TOP_END = x
P['J9'] = (TOP_END + 2.2, 2.6, 90)            # OLED header 1x4, rot 90: pins run +x from pin 1 (left)
# Module at right, U.FL (local -y) facing the right edge: rot -90 maps local -y -> +x
P['U6'] = (W - 1.2 - 7.2, 18.5, -90)
# USB-C on the right edge, mouth (local +y) facing +x: rot 90
P['J1'] = (W - 3.65, min(37.0, BAND_TOP - 7.0), 90)
# LiPo JST-PH on the left edge, mouth (local +y) facing -x: rot -90
P['J4'] = (6.4, 18.0, -90)
# TCA9534 centred above the valve row: P0-P3 (pins 4-7) on its left face the left four channels, P4-P7
# (pins 9-12) on its right face the right four.
P['U7'] = (W / 2, BAND_TOP - 5.0, 0)

# ICs that seed each block (hand-placed inside their regions)
P['U2'] = (26.0, BAND_TOP - 6.0, 0)   # 12 V -> 5 V buck, beside J2 (12 V IN)
# Bootstrap cap and inductor by hand, as the AP63205 datasheet layout: C5 beside pins 6 (BST) / 5 (SW) with its SW end
# dropping onto the SW track, L1 straight out from pin 5. Left to the placer, C5 landed with its SW pad on the far
# side and seven routing rounds never connected it.
P['C5'] = (P['U2'][0] + 3.7, P['U2'][1] - 1.35, 0)    # courtyard just clear of U2's (+-2.1)
P['L1'] = (P['U2'][0] + 8.3, P['U2'][1] + 0.9, 0)     # and L1 just clear of C5
P['U3'] = (15.0, 22.0, 0)             # TP4056, beside the LiPo connector
P['U8'] = (16.0, 15.0, 0)             # SP3485, under J10 (RS485)
P['U5'] = (40.0, 22.0, 0)             # AP2112 LDO, centre of the power block
BLK = json.load(open('blocks.json'))
MID_BOT = BAND_TOP - 1.0                      # middle blocks stop here; below is the gate-line channel and valves
REGION = {   # x0, y0, x1, y1 -- a packed part's courtyard must lie inside its block's region
    'v12':   (11.5, MID_BOT - 14.0, 48.0, MID_BOT),
    'chg':   (0.6, 9.5, 27.0, MID_BOT - 9.0),
    'rs485': (9.0, 9.0, 36.0, 22.0),
    'pwr':   (24.0, 14.0, 60.0, MID_BOT - 6.0),
    'i2c':   (33.0, 9.0, 66.0, MID_BOT),
    'uio':   (44.0, 9.0, 72.0, 26.0),
    'rly':   (0.6, 30.0, 99.4, MID_BOT),
    'mcu':   (58.0, 8.0, 99.4, MID_BOT),
    'usb':   (70.0, 24.0, 99.4, MID_BOT),
}
# decoupling / tight-loop parts: pulled hard to a specific pad (cost x NEAR_W)
NEAR = {'D3': ('D2', '1'), 'R7': ('C4', '1'),
        'C2': ('U2', '3'), 'C3': ('U2', '3'), 'C4': ('U2', '3'),
        'C6': ('L1', '2'), 'C7': ('L1', '2'), 'C8': ('U3', '4'), 'C9': ('U3', '5'), 'C10': ('U4', '5'),
        'C11': ('U5', '1'), 'C12': ('U5', '5'), 'C13': ('U5', '5'), 'C17': ('U6', '3'), 'C18': ('U6', '3'),
        'C19': ('U6', '8'), 'C20': ('U7', '16'), 'C21': ('U8', '8'), 'U1': ('J1', 'A6')}
NEAR_W = 6.0
ORDER = ['v12', 'chg', 'rs485', 'pwr', 'rly', 'i2c', 'uio', 'mcu', 'usb']
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
