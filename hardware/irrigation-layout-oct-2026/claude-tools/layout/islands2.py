import pcbnew
b = pcbnew.LoadBoard('../../esp32_io_board/esp32_io_board.kicad_pcb')
links = [t.GetPosition() for t in b.GetTracks() if t.GetClass() == 'PCB_VIA' and t.GetNetname() == 'GND']
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname() == 'GND' and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH: links.append(p.GetPosition())
isl = []   # (layer, outline)
for z in b.Zones():
    if z.GetNetname() != 'GND' or z.GetIsRuleArea(): continue
    ps = z.GetFilledPolysList(z.GetLayer())
    for i in range(ps.OutlineCount()): isl.append((b.GetLayerName(z.GetLayer()), ps.Outline(i)))
par = list(range(len(isl)))
def find(a):
    while par[a] != a: par[a] = par[par[a]]; a = par[a]
    return a
for pt in links:
    hit = [k for k, (l, ol) in enumerate(isl) if ol.PointInside(pt)]
    for k in hit[1:]: par[find(k)] = find(hit[0])
from collections import defaultdict
grp = defaultdict(list)
for k in range(len(isl)): grp[find(k)].append(k)
main = max(grp.values(), key=lambda g: sum(isl[k][1].Area() for k in g))
for g in grp.values():
    if g is main: continue
    for k in g:
        bb = isl[k][1].BBox()
        print('DETACHED', isl[k][0], round(bb.GetX()/1e6-50, 2), round(bb.GetY()/1e6-50, 2), round(bb.GetWidth()/1e6, 2), 'x', round(bb.GetHeight()/1e6, 2))
print('groups', len(grp), 'islands', len(isl))

# ---- join each detached group to the main group with one via where they overlap on opposite layers ----
import math, sys
if '--fix' in sys.argv:
    mm = pcbnew.FromMM; V = pcbnew.VECTOR2I
    other = []
    for t in b.GetTracks():
        if t.GetNetname() == 'GND': continue
        if t.GetClass() == 'PCB_VIA': other.append(('c', t.GetPosition().x, t.GetPosition().y, t.GetWidth() / 2, None))
        else: other.append(('s', t.GetStart().x, t.GetStart().y, t.GetWidth() / 2, (t.GetEnd().x, t.GetEnd().y)))
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() != 'GND':
                bb = p.GetBoundingBox(); other.append(('b', bb.GetX(), bb.GetY(), 0, (bb.GetRight(), bb.GetBottom())))
    def clear(x, y, r=mm(0.3) + mm(0.25)):
        for k, a, c, w, e in other:
            if k == 'c' and math.hypot(x - a, y - c) < w + r: return False
            if k == 'b' and a - r <= x <= e[0] + r and c - r <= y <= e[1] + r: return False
            if k == 's':
                dx, dy = e[0] - a, e[1] - c; L2 = dx * dx + dy * dy
                u = 0 if L2 == 0 else max(0, min(1, ((x - a) * dx + (y - c) * dy) / L2))
                if math.hypot(a + u * dx - x, c + u * dy - y) < w + r: return False
        return True
    def solid(ol, x, y, r=mm(0.4)):
        return all(ol.PointInside(V(int(x + r * math.cos(k * math.pi / 4)), int(y + r * math.sin(k * math.pi / 4)))) for k in range(8)) and ol.PointInside(V(int(x), int(y)))
    added = []
    for g in grp.values():
        if g is main: continue
        done = False
        for k in g:
            lk, olk = isl[k]; bb = olk.BBox()
            mains = [isl[m][1] for m in main if isl[m][0] != lk]
            x = bb.GetX()
            while x <= bb.GetRight() and not done:
                y = bb.GetY()
                while y <= bb.GetBottom():
                    if solid(olk, x, y) and any(solid(om, x, y) for om in mains) and clear(x, y):
                        added.append((x, y)); done = True; break
                    y += mm(0.2)
                x += mm(0.2)
            if done: break
    gnd = b.FindNet('GND')
    for x, y in added:
        v = pcbnew.PCB_VIA(b); v.SetPosition(V(int(x), int(y))); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(gnd); b.Add(v)
    print('join vias', [(round(x/1e6-50, 2), round(y/1e6-50, 2)) for x, y in added])
    pcbnew.SaveBoard('../../esp32_io_board/esp32_io_board.kicad_pcb', b)
