"""KiCad python, one job: (1) delete dangling track stubs (iterated), (2) add GND stitching vias where both
filled GND pours have solid copper (grid + one per otherwise-unstitched island). Save. Refill in fill.py."""
import pcbnew, math, json
PCB = '../../esp32_io_board/esp32_io_board.kicad_pcb'
b = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM; V = pcbnew.VECTOR2I
# ---------- collect ----------
tracks = [t for t in b.GetTracks()]
segs = []; vias = []
for t in tracks:
    if t.GetClass() == 'PCB_VIA': vias.append((t, t.GetPosition().x, t.GetPosition().y, t.GetNetname()))
    else: segs.append((t, t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y, t.GetLayer(), t.GetNetname(), t.GetWidth()))
pads = []
for f in b.GetFootprints():
    for p in f.Pads():
        bb = p.GetBoundingBox()
        pads.append((p.GetNetname(), bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom(), p.IsOnLayer(pcbnew.F_Cu), p.IsOnLayer(pcbnew.B_Cu)))
zones = {}
for z in b.Zones():
    if z.GetNetname() == 'GND': zones[z.GetLayer()] = z.GetFilledPolysList(z.GetLayer())
TOL = mm(0.05)
def touches(x, y, layer, net, skip):
    for i, (t, x0, y0, x1, y1, l, n, w) in enumerate(segs):
        if i in skip or n != net or l != layer: continue
        if (abs(x0 - x) < TOL and abs(y0 - y) < TOL) or (abs(x1 - x) < TOL and abs(y1 - y) < TOL): return True
        # T-junction onto a segment
        dx, dy = x1 - x0, y1 - y0; L2 = dx * dx + dy * dy
        if L2 > 0:
            u = max(0, min(1, ((x - x0) * dx + (y - y0) * dy) / L2))
            if math.hypot(x0 + u * dx - x, y0 + u * dy - y) < w / 2: return True
    for v, vx, vy, n in vias:
        if n == net and math.hypot(vx - x, vy - y) < mm(0.3): return True
    for n, a, c, d, e, onF, onB in pads:
        if n == net and a - TOL <= x <= d + TOL and c - TOL <= y <= e + TOL and ((layer == pcbnew.F_Cu and onF) or (layer == pcbnew.B_Cu and onB)): return True
    if net == 'GND' and layer in zones and zones[layer].Contains(V(int(x), int(y))): return True
    return False
dead = set()
while True:
    new = set()
    for i, (t, x0, y0, x1, y1, l, n, w) in enumerate(segs):
        if i in dead: continue
        sk = dead | {i}
        if not touches(x0, y0, l, n, sk) or not touches(x1, y1, l, n, sk): new.add(i)
    if not new: break
    dead |= new
# ---------- stitching candidates ----------
F, B = zones.get(pcbnew.F_Cu), zones.get(pcbnew.B_Cu)
def solid(x, y, r=mm(0.75)):
    pts = [(x, y)] + [(x + r * math.cos(k * math.pi / 4), y + r * math.sin(k * math.pi / 4)) for k in range(8)]
    return all(F.Contains(V(int(px), int(py))) and B.Contains(V(int(px), int(py))) for px, py in pts)
e = b.GetBoardEdgesBoundingBox()
existing = [(vx, vy) for v, vx, vy, n in vias]
newv = []
def far(x, y, d=mm(2.5)): return all(math.hypot(x - a, y - c) >= d for a, c in existing + newv)
step = mm(4.0)
y = e.GetY() + mm(2)
while y < e.GetBottom() - mm(2):
    x = e.GetX() + mm(2)
    while x < e.GetRight() - mm(2):
        if solid(x, y) and far(x, y): newv.append((x, y))
        x += step
    y += step
# island-targeted: any F or B island with no via inside it gets one where both layers are solid
def islands(ps):
    return [ps.Outline(i) for i in range(ps.OutlineCount())]
added_isl = 0
for L, ps in ((pcbnew.F_Cu, F), (pcbnew.B_Cu, B)):
    for i in range(ps.OutlineCount()):
        ol = ps.Outline(i); bb = ol.BBox()
        allv = existing + newv
        if any(ol.PointInside(V(int(a), int(c))) for a, c in allv): continue
        found = None
        gx = bb.GetX()
        while gx < bb.GetRight() and not found:
            gy = bb.GetY()
            while gy < bb.GetBottom():
                if ol.PointInside(V(int(gx), int(gy))) and solid(gx, gy, mm(0.6)): found = (gx, gy); break
                gy += mm(0.5)
            gx += mm(0.5)
        if found: newv.append(found); added_isl += 1
# ---------- mutate ----------
for i in dead: b.Remove(segs[i][0])
gnd = b.FindNet('GND')
for x, y in newv:
    v = pcbnew.PCB_VIA(b); v.SetPosition(V(int(x), int(y))); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(gnd); b.Add(v)
info = dict(dangling_removed=len(dead), stitch_vias=len(newv), island_vias=added_isl)
json.dump(info, open('out/post_fix.json', 'w')); print(info)
pcbnew.SaveBoard(PCB, b)
