"""Placement for the ESP32 I/O board. Plain python (no KiCad needed).
Inputs: fp.json (fpmeasure.py), ../schematic/out/netlist.xml. Output: placement.json {ref: [x, y, rot]}, metrics.
Board: W x H mm, origin top-left, y down (KiCad). Rotation in KiCad degrees (CCW on screen).
Decisions (Mitra, 14 Oct 2026): <=100x100, relays along the bottom long edge, other terminals along
the top long edge, USB-C + LiPo on short edges, 4x M3 corner holes, 2 layers."""
import json, math, sys, xml.etree.ElementTree as ET
from collections import defaultdict
W, H = 100.0, float(sys.argv[1]) if len(sys.argv) > 1 else 80.0
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
# Relay channels along the bottom: terminal (wire entry +y local -> rot 0 faces bottom edge) and relay rotated
# -90 so NO/NC end faces the terminal and COM (relay pad 1) sits directly above terminal pad 2 (COM).
PITCH = 17.0; X0 = W / 2 - (3 * PITCH + 16.34) / 2 + 3.08
TY = H - 5.6                                  # terminal pin row -> body front ~1 mm inside bottom edge
RY = TY - 5.75 - 0.3 - 18.59                  # relay origin: relay courtyard bottom just above terminal's
for i in range(4):
    x = X0 + i * PITCH
    P[f'J{12 + i}'] = (x, TY, 0)
    P[f'K{1 + i}'] = (x + 5.08, RY, -90)
# Top edge terminals: rot 180 so wire entry faces the top edge. Pin 1 is then the rightmost pin.
top = [('J2', 5.6, 8.18), ('J11', 4.4, 9.69), ('J8', 4.4, 9.69), ('J6', 4.4, 4.62), ('J7', 4.4, 4.62)]
x = 9.0
for ref, py, right in top:                    # 'right' = local +x extent; after rot 180 it is the left extent
    left = x + right; P[ref] = (left, py, 180); x = left - FP[ref]['bbox'][0] + 1.0
TOP_END = x
P['J9'] = (TOP_END + 2.2, 2.6, 90)            # OLED header 1x4, rot 90: pins run +x from pin 1 (left)
# Module at right, U.FL (local -y) facing the right edge: rot -90 maps local -y -> +x
P['U6'] = (W - 1.2 - 7.2, 18.5, -90)
# USB-C on the right edge, mouth (local +y) facing +x: rot 90
P['J1'] = (W - 3.65, 37.0, 90)
# LiPo JST-PH on the left edge, mouth (local +y) facing -x: rot -90
P['J4'] = (6.4, 30.0, -90)
# ULN2003 above relays K2/K3, outputs (pins 10-16, right side local) facing down: rot 90
P['U9'] = (W / 2, RY - 1.59 - 0.6 - 3.75, 90)

# ICs that seed each block (hand-placed inside their regions)
P['U2'] = (12.0, 21.0, 0)       # 12 V -> 5 V buck, under J2 (12 V IN)
P['U3'] = (14.0, 40.0, 0)       # TP4056, beside the LiPo connector
P['U8'] = (28.0, 17.0, 0)       # SP3485, under J11 (RS485)
P['U5'] = (37.0, 29.0, 0)       # AP2112 LDO, centre of the power block
P['U7'] = (37.0, 42.0, 90)      # TCA9534, next to the ULN2003
BLK = json.load(open('blocks.json'))
REGION = {   # x0, y0, x1, y1 -- a packed part's courtyard must lie inside its block's region
    'v12':   (0.6, 11.0, 25.0, 31.0),
    'chg':   (0.6, 29.0, 25.0, 47.6),
    'rs485': (20.0, 9.0, 40.0, 24.0),
    'pwr':   (24.0, 22.0, 50.0, 47.6),
    'i2c':   (33.0, 9.0, 50.0, 24.0),
    'uio':   (46.0, 9.0, 66.0, 26.0),
    'rly':   (12.0, 33.0, 88.0, 47.6),
    'mcu':   (60.0, 8.0, 99.4, 47.6),
    'usb':   (74.0, 26.0, 99.4, 47.6),
}
# decoupling / tight-loop parts: pulled hard to a specific pad (cost x NEAR_W)
NEAR = {'C2': ('U2', '3'), 'C3': ('U2', '3'), 'C4': ('U2', '3'), 'C5': ('U2', '6'), 'L1': ('U2', '5'),
        'C6': ('L1', '2'), 'C7': ('L1', '2'), 'C8': ('U3', '4'), 'C9': ('U3', '5'), 'C10': ('U4', '5'),
        'C11': ('U5', '1'), 'C12': ('U5', '5'), 'C13': ('U5', '5'), 'C17': ('U6', '3'), 'C18': ('U6', '3'),
        'C19': ('U6', '8'), 'C20': ('U7', '16'), 'C21': ('U8', '8'), 'U1': ('J1', 'A6')}
NEAR_W = 6.0
BLK['J10'] = 'rly'                                   # expander spare header beside the TCA9534
ORDER = ['v12', 'chg', 'rs485', 'pwr', 'rly', 'i2c', 'uio', 'mcu', 'usb']
FIXED = set(P)
RESERVED = [[X0 - 3.08 - 0.3, RY - 1.59 - 0.3, X0 + 3 * PITCH + 13.26 + 0.3, H]]   # relay/terminal band
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
json.dump(dict(W=W, H=H, holes=HOLES, place={r: [round(v[0], 3), round(v[1], 3), v[2]] for r, v in P.items()}),
          open('placement.json', 'w'), indent=0)
print(f'board {W} x {H}: placed {len(P)}; ratsnest {L:.0f} mm excl. GND; crossings {X}')
