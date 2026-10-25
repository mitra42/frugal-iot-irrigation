"""KiCad python, one job: delete DRC-named dangling tracks + router-made GND tracks on B.Cu, and put a GND via
into every filled GND island (either layer) that has no via/THT GND pad, with clearance from other-net copper."""
import pcbnew, json, math
PCB = '../../esp32_io_board/esp32_io_board.kicad_pcb'
b = pcbnew.LoadBoard(PCB); mm = pcbnew.FromMM; V = pcbnew.VECTOR2I
drc = json.load(open('out/drc.json'))
dead_ids = {i['uuid'] for v in drc['violations'] if v['type'] == 'track_dangling' for i in v['items']}
# ---- collect ----
kill = []; vias = []; other = []   # other: (kind, geometry) of non-GND copper
for t in b.GetTracks():
    u = t.m_Uuid.AsString()
    if t.GetClass() == 'PCB_VIA':
        vias.append((t.GetPosition().x, t.GetPosition().y))
        if t.GetNetname() != 'GND': other.append(('c', t.GetPosition().x, t.GetPosition().y, t.GetWidth() / 2, None))
        continue
    if u in dead_ids or (t.GetNetname() == 'GND' and t.GetLayer() == pcbnew.B_Cu):
        kill.append(t); continue
    if t.GetNetname() != 'GND':
        other.append(('s', t.GetStart().x, t.GetStart().y, t.GetWidth() / 2, (t.GetEnd().x, t.GetEnd().y)))
thts = []
for f in b.GetFootprints():
    for p in f.Pads():
        bb = p.GetBoundingBox()
        if p.GetNetname() == 'GND' and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH: thts.append((p.GetPosition().x, p.GetPosition().y))
        if p.GetNetname() != 'GND': other.append(('b', bb.GetX(), bb.GetY(), 0, (bb.GetRight(), bb.GetBottom())))
polys = {z.GetLayer(): z.GetFilledPolysList(z.GetLayer()) for z in b.Zones() if z.GetNetname() == 'GND'}
CL = mm(0.3) + mm(0.25)        # via radius + clearance
def clear(x, y):
    for k, a, c, r, e in other:
        if k == 'c' and math.hypot(x - a, y - c) < r + CL: return False
        if k == 'b' and a - CL <= x <= e[0] + CL and c - CL <= y <= e[1] + CL: return False
        if k == 's':
            dx, dy = e[0] - a, e[1] - c; L2 = dx * dx + dy * dy
            u = 0 if L2 == 0 else max(0, min(1, ((x - a) * dx + (y - c) * dy) / L2))
            if math.hypot(a + u * dx - x, c + u * dy - y) < r + CL: return False
    return True
anchors = vias + thts
newv = []
for L, ps in polys.items():
    for i in range(ps.OutlineCount()):
        ol = ps.Outline(i)
        if any(ol.PointInside(V(int(a), int(c))) for a, c in anchors + newv): continue
        bb = ol.BBox(); found = None
        gx = bb.GetX()
        while gx <= bb.GetRight() and not found:
            gy = bb.GetY()
            while gy <= bb.GetBottom():
                pts = [(gx, gy)] + [(gx + mm(0.35) * math.cos(k * math.pi / 4), gy + mm(0.35) * math.sin(k * math.pi / 4)) for k in range(8)]
                if all(ol.PointInside(V(int(px), int(py))) for px, py in pts) and clear(gx, gy):
                    found = (gx, gy); break
                gy += mm(0.2)
            gx += mm(0.2)
        if found: newv.append(found)
        else: print('no via spot for island on', 'F' if L == pcbnew.F_Cu else 'B', 'bbox mm', round(bb.GetX()/1e6-50,1), round(bb.GetY()/1e6-50,1), round(bb.GetWidth()/1e6,1), round(bb.GetHeight()/1e6,1))
# ---- mutate ----
for t in kill: b.Remove(t)
gnd = b.FindNet('GND')
for x, y in newv:
    v = pcbnew.PCB_VIA(b); v.SetPosition(V(int(x), int(y))); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(gnd); b.Add(v)
print({'tracks_removed': len(kill), 'island_vias': len(newv)})
pcbnew.SaveBoard(PCB, b)
