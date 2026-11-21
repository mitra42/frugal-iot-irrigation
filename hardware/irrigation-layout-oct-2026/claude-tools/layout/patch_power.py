"""KiCad python, one-off, one job: bring the routed V0.2 board up to the power changes made in the schematic on
21 Nov 2026 (D87-D89), without re-laying it out. Run after ../schematic/run_kicad.sh; then route what it leaves
open (route_patch.sh). Writes out/patch_power.json before saving.
  D87  DW01A + FS8205A + R14 + R15 -> XB5353A: U4 becomes SOT-23-5 in the same place; R14, R15, Q1 removed;
       C10 re-netted to VBAT/CELL_NEG. Copper on nets that no longer exist, and on /CELL_NEG, is removed, and so
       is any VBAT or GND track left dangling by the removed pads - the router redoes those few connections.
  D88  AP2112K -> RT9080: U5 SOT-23-5 -> TSOT-23-5. Identical pads (checked), so its copper stays.
  D89  VSYS is a named net now (was Net-(D7-K)), and nine test points TP1-TP9. Each test pad goes in the
       free spot (clear of every courtyard, with room for its label) nearest its own rail's top copper, so the
       router has at most a short stub to add; GND's lands in the pour. They sit near their own circuits rather
       than in one group as on the LoRa board: grouping would mean eight new tracks across an already full board.
Why a patch and not pipeline.sh: a full re-layout re-routes everything (with the hand fixes of D83) for a change
that touches one corner. place.py still knows the old parts; see D87 for what a full rebuild would need."""
import json, math, xml.etree.ElementTree as ET, pcbnew
PCB = '../../esp32_io_board/esp32_io_board.kicad_pcb'
LIB = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'
b = pcbnew.LoadBoard(PCB); mm = pcbnew.FromMM; tomm = lambda v: v / 1e6; V = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
F = pcbnew.F_Cu
REMOVE = {'R14', 'R15', 'Q1'}
GONE_NETS = {'Net-(Q1A-G)', 'Net-(Q1B-G)', 'Net-(U4-CS)', 'Net-(U4-VCC)', 'Net-(Q1A-D)', '/CELL_NEG',
             'unconnected-(U4-TD-Pad4)'}
RENAME = {'Net-(D7-K)': 'VSYS'}
# ---- new netlist ----
nl = ET.parse('../schematic/out/netlist.xml').getroot()
padnet = {(nd.get('ref'), nd.get('pin')): n.get('name') for n in nl.iter('net') for nd in n.iter('node')}
comp = {c.get('ref'): dict(value=c.findtext('value'), fp=c.findtext('footprint'), ts=c.findtext('tstamps'),
                           fields={f.get('name'): f.text or '' for f in c.iter('field')}) for c in nl.iter('comp')}
TPS = sorted([r for r in comp if r.startswith('TP')], key=lambda r: int(r[2:]))
def load(fpname):
    lib, name = fpname.split(':')
    fp = pcbnew.FootprintLoad(f'{LIB}/{lib}.pretty', name); fp.SetFPID(pcbnew.LIB_ID(lib, name)); return fp
# ---- collect (no reads after mutation) ----
fps = {f.GetReference(): f for f in b.GetFootprints()}
u4p, u4r = fps['U4'].GetPosition(), fps['U4'].GetOrientationDegrees()
u5p, u5r = fps['U5'].GetPosition(), fps['U5'].GetOrientationDegrees()
# pads after the change: (net, layerset-on-F, bbox, x, y); the new U4's from a free-standing copy of its footprint
newu4 = load(comp['U4']['fp']); newu4.SetPosition(u4p); newu4.SetOrientationDegrees(u4r)
pads = []
def padrec(p, net):
    bb = p.GetBoundingBox(); q = p.GetPosition()
    return dict(net=net, F=p.IsOnLayer(F), B=p.IsOnLayer(pcbnew.B_Cu),
                box=(tomm(bb.GetX()), tomm(bb.GetY()), tomm(bb.GetRight()), tomm(bb.GetBottom())), x=tomm(q.x), y=tomm(q.y))
for r, f in fps.items():
    if r in REMOVE or r == 'U4': continue
    for p in f.Pads():
        if not p.GetNumber(): continue
        pads.append(padrec(p, padnet.get((r, p.GetNumber()), p.GetNetname())))
for p in newu4.Pads(): pads.append(padrec(p, padnet[('U4', p.GetNumber())]))
items = []   # tracks and vias, with their nets after the rename
for t in b.GetTracks():
    net = RENAME.get(t.GetNetname(), t.GetNetname())
    if t.GetClass() == 'PCB_VIA':
        q = t.GetPosition(); items.append(dict(obj=t, via=True, net=net, x=tomm(q.x), y=tomm(q.y), w=tomm(t.GetWidth(F))))
    else:
        s, e = t.GetStart(), t.GetEnd()
        items.append(dict(obj=t, via=False, net=net, layer=t.GetLayer(), a=(tomm(s.x), tomm(s.y)), b=(tomm(e.x), tomm(e.y)),
                          w=tomm(t.GetWidth())))
kill = {id(it['obj']) for it in items if it['net'] in GONE_NETS}
# dangling trim: a track end must land on a same-net pad on its layer, a same-net via, or another live track end
def inbox(x, y, bx, m=0.0): return bx[0] - m <= x <= bx[2] + m and bx[1] - m <= y <= bx[3] + m
def end_ok(it, pt):
    x, y = pt; L = 'F' if it['layer'] == F else 'B'
    if any(p['net'] == it['net'] and p[L] and inbox(x, y, p['box']) for p in pads): return True
    for o in items:
        if o is it or id(o['obj']) in kill or o['net'] != it['net']: continue
        if o['via'] and math.hypot(o['x'] - x, o['y'] - y) < o['w'] / 2: return True
        if not o['via'] and o['layer'] == it['layer'] and any(math.hypot(q[0] - x, q[1] - y) < 0.01 for q in (o['a'], o['b'])):
            return True
        if not o['via'] and o['layer'] == it['layer'] and seg_dist(x, y, o['a'], o['b']) < 0.01: return True
    return False
def seg_dist(x, y, a, c):
    dx, dy = c[0] - a[0], c[1] - a[1]; L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / L2))
    return math.hypot(x - a[0] - t * dx, y - a[1] - t * dy)
changed = True
while changed:
    changed = False
    for it in items:
        if id(it['obj']) in kill or it['via'] or it['net'] not in ('VBAT', 'GND'): continue
        if not (end_ok(it, it['a']) and end_ok(it, it['b'])): kill.add(id(it['obj'])); changed = True
trimmed = [(it['net'], it['a'], it['b']) for it in items if id(it['obj']) in kill and not it['via'] and it['net'] in ('VBAT', 'GND')]
live = [it for it in items if id(it['obj']) not in kill]
# ---- test pad positions ----
edge = b.GetBoardEdgesBoundingBox(); EX0, EY0, EX1, EY1 = (tomm(edge.GetX()), tomm(edge.GetY()), tomm(edge.GetRight()), tomm(edge.GetBottom()))
crt = []
for r, f in fps.items():
    if r in REMOVE: continue
    try:
        bb = (newu4 if r == 'U4' else f).GetCourtyard(F).BBox()
        if bb.GetWidth() > 0: crt.append((r, (tomm(bb.GetX()), tomm(bb.GetY()), tomm(bb.GetRight()), tomm(bb.GetBottom()))))
    except Exception: pass
R_PAD, CLR = 0.75, 0.35
# the pad's courtyard (r 1.3) plus its rail-name label below it (0.8 mm text, up to 7 characters)
KEEP = (-2.4, -1.3, 2.4, 2.4)
def boxes_hit(a, c): return a[0] < c[2] and c[0] < a[2] and a[1] < c[3] and c[1] < a[3]
# copper on F.Cu as (net, kind, geometry), bucketed on a 2 mm grid so each candidate only looks nearby
cu = []
for p in pads:
    if p['F']: cu.append((p['net'], 'box', p['box'], 0.0))
for o in live:
    if o['via']: cu.append((o['net'], 'pt', (o['x'], o['y']), o['w'] / 2))
    elif o['layer'] == F: cu.append((o['net'], 'seg', (o['a'], o['b']), o['w'] / 2))
def cdist(x, y, c):
    _, k, g, r = c
    if k == 'box': return math.hypot(max(g[0] - x, 0, x - g[2]), max(g[1] - y, 0, y - g[3]))
    if k == 'pt': return math.hypot(g[0] - x, g[1] - y) - r
    return seg_dist(x, y, g[0], g[1]) - r
BK = {}
for c in cu:
    k, g = c[1], c[2]
    xs = (g[0], g[2]) if k == 'box' else ((g[0],) if k == 'pt' else (g[0][0], g[1][0]))
    ys = (g[1], g[3]) if k == 'box' else ((g[1],) if k == 'pt' else (g[0][1], g[1][1]))
    for i in range(int((min(xs) - 3) // 2), int((max(xs) + 3) // 2) + 1):
        for j in range(int((min(ys) - 3) // 2), int((max(ys) + 3) // 2) + 1): BK.setdefault((i, j), []).append(c)
grid = []    # (x, y, {net: distance from the pad's edge}) for every spot whose courtyard and label are clear
for i in range(int((EX0 + 2) * 2), int((EX1 - 2) * 2) + 1):
    for j in range(int((EY0 + 2) * 2), int((EY1 - 2.5) * 2) + 1):
        x, y = i / 2, j / 2
        kb = (x + KEEP[0], y + KEEP[1], x + KEEP[2], y + KEEP[3])
        if any(boxes_hit(kb, bx) for _, bx in crt): continue
        dn = {}
        for c in BK.get((int(x // 2), int(y // 2)), []):
            d = cdist(x, y, c) - R_PAD
            if d < dn.get(c[0], 9.0): dn[c[0]] = d
        grid.append((x, y, dn))
CENTRE = (50.0 + 30.0, 50.0 + 22.0)    # page coordinates: the power area (charger, load sharing, LDO)
chosen = []; place = {}
for ref in TPS:
    net = padnet[(ref, '1')]
    # the rail's copper on either layer: a stub may end at a via or a through-hole pad
    mine = [(p['net'], 'box', p['box'], 0.0) for p in pads if p['net'] == net]
    mine += [(o['net'], 'pt', (o['x'], o['y']), o['w'] / 2) if o['via'] else (o['net'], 'seg', (o['a'], o['b']), o['w'] / 2)
             for o in live if o['net'] == net]
    best = None
    for x, y, dn in grid:
        room = min([d for n, d in dn.items() if n != net] + [9.0])
        if room < CLR: continue
        if any(math.hypot(x - x0, y - y0) < 5.2 or (abs(x - x0) < 4.8 and abs(y - y0) < 3.7) for x0, y0 in chosen): continue
        own = 0.0 if net == 'GND' else max(min(cdist(x, y, c) for c in mine) - R_PAD, 0.0)   # stub to the rail
        s = -own * 3 - math.hypot(x - CENTRE[0], y - CENTRE[1]) * 0.1 + min(room, 1.0)
        if best is None or s > best[0]: best = (s, x, y, room, own)
    assert best, (ref, net, 'no room anywhere')
    chosen.append((best[1], best[2]))
    place[ref] = dict(net=net, x=best[1], y=best[2], room=round(best[3], 2), stub=round(best[4], 2))
report = dict(trimmed=trimmed, killed=len(kill), tps=place)
json.dump(report, open('out/patch_power.json', 'w'), indent=1)
# ---- mutate ----
for it in items:
    if id(it['obj']) in kill: b.Remove(it['obj'])
netobj = {}
def N(name):
    if name not in netobj:
        netobj[name] = b.FindNet(name) or None
        if netobj[name] is None:
            ni = pcbnew.NETINFO_ITEM(b, name); b.Add(ni); netobj[name] = ni
    return netobj[name]
for it in items:
    if id(it['obj']) not in kill and it['net'] == 'VSYS': it['obj'].SetNet(N('VSYS'))
def setup(fp, ref, pos=None, rot=0):
    c = comp[ref]
    fp.SetReference(ref); fp.SetValue(c['value']); fp.SetPath(pcbnew.KIID_PATH('/' + c['ts']))
    if pos is not None: fp.SetPosition(pos)
    fp.SetOrientationDegrees(rot)
    return fp
old = {r: fps[r] for r in REMOVE | {'U4', 'U5'}}
keep_txt = {r: (old[r].Reference().GetPosition(), old[r].Reference().GetTextAngleDegrees(), old[r].Reference().IsVisible())
            for r in ('U4', 'U5')}
for r in old: b.Remove(old[r])
newu4 = setup(load(comp['U4']['fp']), 'U4', u4p, u4r); b.Add(newu4)
newu5 = setup(load(comp['U5']['fp']), 'U5', u5p, u5r); b.Add(newu5)
added = [newu4, newu5]
for ref in TPS:
    t = place[ref]; fp = setup(load(comp[ref]['fp']), ref, V(t['x'], t['y']))
    fp.SetAttributes(fp.GetAttributes() & ~pcbnew.FP_EXCLUDE_FROM_BOM)      # match the symbol, as the LoRa board
    b.Add(fp); added.append(fp)
for fp in added:                                   # nets and fields AFTER board.Add
    r = fp.GetReference()
    for p in fp.Pads(): p.SetNet(N(padnet[(r, p.GetNumber())]))
    for k, v in comp[r]['fields'].items():
        if k in ('Footprint', 'Datasheet', 'Value', 'Reference'): continue
        fp.SetField(k, v)
        for fld in fp.GetFields():
            if fld.GetName() == k: fld.SetVisible(False); fld.SetLayer(pcbnew.F_Fab)
    if r in keep_txt:
        pos, ang, vis = keep_txt[r]; fp.Reference().SetPosition(pos); fp.Reference().SetTextAngleDegrees(ang); fp.Reference().SetVisible(vis)
    if r.startswith('TP'):                         # the silkscreen names the rail, not TPn (as the LoRa board, L20)
        fp.Reference().SetVisible(False)
        v = fp.Value(); v.SetLayer(pcbnew.F_SilkS); v.SetVisible(True)
        v.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8))); v.SetTextThickness(mm(0.12))
        v.SetPosition(V(place[r]['x'], place[r]['y'] + 1.6))
for f in b.GetFootprints():
    if f.GetReference() == 'C10':
        for p in f.Pads(): p.SetNet(N(padnet[('C10', p.GetNumber())]))
    for p in f.Pads():
        if p.GetNetname() in RENAME: p.SetNet(N(RENAME[p.GetNetname()]))
pcbnew.SaveBoard(PCB, b)
print('killed', len(kill), 'trimmed', len(trimmed), 'TPs', {r: (v['net'], v['x'], v['y'], v['room']) for r, v in place.items()})
